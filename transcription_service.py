#!/usr/bin/env python3
"""
Abstract transcription service interface for supporting multiple transcription backends.
Supports both local Whisper models and cloud-based AWS Transcribe.
"""

from abc import ABC, abstractmethod
from pynput import keyboard
import time
import pyperclip
from accessibility_utils import check_accessibility_permissions, get_accessibility_instructions, prompt_for_permissions, _execute_applescript_safely


class TranscriptionService(ABC):
    """Abstract base class for transcription services"""
    
    def __init__(self):
        self.pykeyboard = keyboard.Controller()
    
    @abstractmethod
    def transcribe(self, audio_data, language=None):
        """
        Transcribe audio data and return the result.
        
        Args:
            audio_data: Audio data in numpy float32 format
            language: Optional language code for transcription
            
        Returns:
            str: Transcribed text
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up any resources used by the transcription service"""
        pass
    
    def type_text(self, text):
        """Type the transcribed text with accessibility permission checking and clipboard fallback"""
        print(f"Transcribed: {text}")
        
        if not text or text.strip() == "":
            print("No text to type")
            return
        
        # Sanitize text to prevent clipboard issues
        text = text.strip()
        # Remove any null bytes or other problematic characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        if not text:
            print("No valid text after sanitization")
            return
        
        # Preserve original clipboard content
        original_clipboard = None
        try:
            original_clipboard = pyperclip.paste()
            print(f"Preserving original clipboard content ({len(original_clipboard) if original_clipboard else 0} chars)")
        except Exception as e:
            print(f"Warning: Could not read original clipboard: {e}")
        
        # Check accessibility permissions first
        if not check_accessibility_permissions():
            print("Accessibility permissions required!")
            print(get_accessibility_instructions())
            
            # Offer clipboard fallback (no restoration needed since user will paste manually)
            print("Copying text to clipboard as fallback...")
            try:
                pyperclip.copy(text)
                print(f"Text copied to clipboard: '{text}'")
                print("Paste using Cmd+V")
                print("Note: Original clipboard content will be restored after you paste")
                return
            except Exception as e:
                print(f"Clipboard error: {e}")
                print(f"Manual copy needed: {text}")
                return
        
        # Multi-tier approach with clipboard verification
        success = False
        
        # Method 1: Verified clipboard + AppleScript paste (most reliable)
        try:
            
            # Copy to clipboard and verify with retries
            copy_success = False
            for retry in range(3):
                pyperclip.copy(text)
                time.sleep(0.2)  # Longer pause for clipboard update
                
                # Verify clipboard contents
                clipboard_content = pyperclip.paste()
                if clipboard_content == text:
                    copy_success = True
                    break
                else:
                    time.sleep(0.1)
            
            if copy_success:
                # Use AppleScript for reliable paste on macOS
                try:
                    import subprocess
                    applescript = 'tell application "System Events" to keystroke "v" using command down'
                    result = subprocess.run(['osascript', '-e', applescript], 
                                          capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        # Wait for paste to complete before proceeding
                        time.sleep(0.3)
                        success = True
                except Exception as e:
                    pass
                
        except Exception as e:
            print(f"AppleScript method failed: {e}")
        
        # Method 2: Verified clipboard + PyKeyboard (fallback)
        if not success:
            try:
                
                # Ensure clipboard is updated with retries
                copy_success = False
                for retry in range(3):
                    pyperclip.copy(text)
                    time.sleep(0.2)
                    
                    # Verify clipboard
                    if pyperclip.paste() == text:
                        copy_success = True
                        break
                    else:
                        time.sleep(0.1)
                
                if copy_success:
                    # Use PyKeyboard with corrected key sequence
                    self.pykeyboard.press(keyboard.Key.cmd)
                    self.pykeyboard.press('v')
                    time.sleep(0.1)  # Hold the combination
                    self.pykeyboard.release('v')
                    self.pykeyboard.release(keyboard.Key.cmd)
                    
                    # Wait for paste to complete
                    time.sleep(0.3)
                    success = True
                    
            except Exception as e:
                print(f"PyKeyboard method failed: {e}")
        
        # Method 3: Optimized typing (reliable fallback)
        if not success:
            try:
                self.pykeyboard.type(text)
                success = True
                
            except Exception as e:
                print(f"Typing method failed: {e}")
        
        # Method 4: Clipboard-only (final fallback)
        if not success:
            try:
                pyperclip.copy(text)
                
            except Exception as e:
                print(f"All methods failed: {e}")
                print(f"Manual input required: '{text}'")
                print(f"Manual copy: {text}")
        
        # Wait before restoring clipboard to ensure paste completed
        if success:
            time.sleep(0.5)  # Additional delay after paste completion
        
        # Restore original clipboard content
        self._restore_clipboard(original_clipboard)
    
    def _restore_clipboard(self, original_content):
        """Restore the original clipboard content with verification"""
        if original_content is not None:
            try:
                # Restore with retries to ensure it takes
                for retry in range(3):
                    pyperclip.copy(original_content)
                    time.sleep(0.1)
                    
                    # Verify restoration
                    if pyperclip.paste() == original_content:
                        return
                    else:
                        time.sleep(0.1)
            except Exception as e:
                pass


class WhisperTranscriptionService(TranscriptionService):
    """Local Whisper transcription service"""
    
    def __init__(self, model):
        super().__init__()
        self.model = model
    
    def transcribe(self, audio_data, language=None):
        """Transcribe using local Whisper model"""
        print("Starting Whisper transcription...")
        try:
            result = self.model.transcribe(audio_data, language=language)
            text = result['text']
            print(f"Transcription completed: '{text}'")
            self.type_text(text)
            return text
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return ""
    
    def cleanup(self):
        """Clean up Whisper model resources"""
        # Whisper models don't require explicit cleanup
        pass


class AWSTranscriptionService(TranscriptionService):
    """AWS Transcribe streaming transcription service"""
    
    def __init__(self, region_name='us-east-1'):
        super().__init__()
        self.region_name = region_name
        self._setup_aws_client()
    
    def _setup_aws_client(self):
        """Initialize AWS Transcribe streaming client"""
        try:
            import boto3
            import os
            from amazon_transcribe.client import TranscribeStreamingClient
            
            # Get AWS credentials from boto3 session (respects AWS_PROFILE and credentials file)
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                raise Exception("No AWS credentials found. Please configure AWS credentials using 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
            
            print("🔵 AWS TRANSCRIBE SERVICE: AWS credentials loaded successfully")
            
            # Store credentials securely without exposing them in environment
            # Pass credentials directly to the client instead of using environment variables
            self.aws_credentials = {
                'access_key': credentials.access_key,
                'secret_key': credentials.secret_key,
                'session_token': credentials.token if credentials.token else None
            }
            
            # Initialize TranscribeStreamingClient with explicit credentials
            # Note: This may require modification based on amazon-transcribe library API
            try:
                self.transcribe_client = TranscribeStreamingClient(
                    region=self.region_name,
                    aws_access_key_id=credentials.access_key,
                    aws_secret_access_key=credentials.secret_key,
                    aws_session_token=credentials.token
                )
            except TypeError:
                # Fallback: Use environment variables temporarily only for this process
                # Set them right before client creation and clear afterwards
                original_env = {}
                env_keys = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION']
                
                # Backup original environment
                for key in env_keys:
                    if key in os.environ:
                        original_env[key] = os.environ[key]
                
                # Set credentials temporarily
                os.environ['AWS_ACCESS_KEY_ID'] = credentials.access_key
                os.environ['AWS_SECRET_ACCESS_KEY'] = credentials.secret_key
                if credentials.token:
                    os.environ['AWS_SESSION_TOKEN'] = credentials.token
                os.environ['AWS_DEFAULT_REGION'] = self.region_name
                
                try:
                    self.transcribe_client = TranscribeStreamingClient(region=self.region_name)
                finally:
                    # Clear AWS credentials from environment immediately
                    for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN']:
                        if key in os.environ:
                            del os.environ[key]
                    
                    # Restore original environment
                    for key, value in original_env.items():
                        os.environ[key] = value
            print(f"🔵 AWS TRANSCRIBE SERVICE: Initialized with region {self.region_name}")
            
        except ImportError as e:
            if 'amazon_transcribe' in str(e):
                raise ImportError("amazon-transcribe is required for AWS Transcribe streaming. Install with: pip install amazon-transcribe")
            elif 'boto3' in str(e):
                raise ImportError("boto3 is required for AWS Transcribe. Install with: pip install boto3")
            else:
                raise e
        except Exception as e:
            raise Exception(f"Failed to initialize AWS Transcribe streaming client: {e}")
    
    def transcribe(self, audio_data, language=None):
        """Transcribe using AWS Transcribe streaming API"""
        print("Starting AWS transcription...")
        try:
            import asyncio
            import numpy as np
            
            # Convert float32 audio to int16 PCM bytes
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Run async transcription
            text = asyncio.run(self._transcribe_streaming(audio_bytes, language))
            print(f"AWS transcription completed: '{text}'")
            self.type_text(text)
            return text
                    
        except Exception as e:
            print(f"AWS transcription error: {e}")
            return ""
    
    async def _transcribe_streaming(self, audio_bytes, language=None):
        """Transcribe audio using AWS Transcribe streaming"""
        try:
            import asyncio
            from amazon_transcribe.handlers import TranscriptResultStreamHandler
            from amazon_transcribe.model import TranscriptEvent
            import io
            
            language_code = self._map_language_code(language) if language else 'en-US'
            
            # Start transcription stream first
            stream = await self.transcribe_client.start_stream_transcription(
                language_code=language_code,
                media_sample_rate_hz=16000,
                media_encoding='pcm'
            )
            
            # Create a simple handler to collect results with the required stream parameter
            class SimpleHandler(TranscriptResultStreamHandler):
                def __init__(self, transcript_result_stream):
                    super().__init__(transcript_result_stream)
                    self.transcript_parts = []
                    self.final_transcript = ""
                
                async def handle_transcript_event(self, transcript_event: TranscriptEvent):
                    results = transcript_event.transcript.results
                    for result in results:
                        if not result.is_partial:
                            for alt in result.alternatives:
                                self.transcript_parts.append(alt.transcript)
                                self.final_transcript = " ".join(self.transcript_parts)
            
            handler = SimpleHandler(stream.output_stream)
            
            # Create audio stream generator
            async def audio_generator():
                # Send audio in chunks
                chunk_size = 1024 * 2  # 2KB chunks
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0.01)  # Small delay to simulate streaming
            
            # Send audio and handle results
            async def send_audio():
                async for chunk in audio_generator():
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                await stream.input_stream.end_stream()
            
            # Start handling results as a separate task
            async def handle_stream():
                try:
                    async for event in stream.output_stream:
                        await handler.handle_transcript_event(event)
                except Exception as e:
                    print(f"🔴 Stream handling error: {e}")
            
            handler_task = asyncio.create_task(handle_stream())
            
            # Send audio data
            await send_audio()
            
            # Wait for stream to complete naturally with timeout
            try:
                await asyncio.wait_for(handler_task, timeout=10.0)
            except asyncio.TimeoutError:
                print("🟡 Stream handling timed out after 10 seconds")
                handler_task.cancel()
                try:
                    await handler_task
                except asyncio.CancelledError:
                    pass
            
            return handler.final_transcript.strip()
            
        except Exception as e:
            print(f"Error in streaming transcription: {e}")
            return ""
    
    def _map_language_code(self, whisper_lang):
        """Map Whisper language codes to AWS Transcribe language codes"""
        mapping = {
            'en': 'en-US',
            'es': 'es-US',
            'fr': 'fr-FR',
            'de': 'de-DE',
            'it': 'it-IT',
            'pt': 'pt-BR',
            'ja': 'ja-JP',
            'ko': 'ko-KR',
            'zh': 'zh-CN'
        }
        return mapping.get(whisper_lang, 'en-US')
    
    def cleanup(self):
        """Clean up AWS resources"""
        # AWS streaming clients don't require explicit cleanup
        pass