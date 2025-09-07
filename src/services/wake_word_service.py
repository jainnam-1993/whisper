#!/usr/bin/env python3
"""
Enhanced RealtimeSTT Wrapper with Wake Word Support
Extends the basic RealtimeSTT wrapper to include voice activation capabilities
"""

from RealtimeSTT import AudioToTextRecorder
from ..backends.transcription_base import TranscriptionService
import time
import subprocess


class ClipboardManager:
    """Handles copying text to clipboard with preservation support"""
    
    def __init__(self):
        self.preserved_content = None
    
    def preserve_clipboard(self):
        """Preserve current clipboard content"""
        try:
            result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
            self.preserved_content = result.stdout
            return True
        except Exception:
            self.preserved_content = None
            return False
    
    def restore_clipboard(self):
        """Restore previously preserved clipboard content"""
        if self.preserved_content is not None:
            try:
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, close_fds=True)
                process.communicate(input=self.preserved_content.encode('utf-8'))
                return True
            except:
                pass
        return False
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, close_fds=True)
            process.communicate(input=text.encode('utf-8'))
            return True
        except:
            return False
    
    def paste_from_clipboard(self):
        """Paste using AppleScript - most reliable on macOS"""
        try:
            from accessibility_utils import _execute_applescript_safely
            result = _execute_applescript_safely(
                'tell application "System Events" to keystroke "v" using command down'
            )
            return result is not None
        except:
            # Fallback to keyboard simulation
            try:
                from pynput import keyboard
                keyboard_controller = keyboard.Controller()
                with keyboard_controller.pressed(keyboard.Key.cmd):
                    keyboard_controller.press('v')
                    keyboard_controller.release('v')
                return True
            except:
                return False


class WakeWordRealtimeSTTWrapper(TranscriptionService):
    """
    Enhanced RealtimeSTT wrapper with wake word detection support.
    
    Features:
    - Voice activation with "computer", "hey google", etc.
    - Hands-free operation - no keyboard triggers needed
    - Same Whisper transcription quality
    - Configurable wake word sensitivity and timeout
    """
    
    def __init__(self, model="base", language="en", wake_word="computer", 
                 sensitivity=0.6, timeout=0, post_speech_silence_duration=1.5,
                 silero_sensitivity=0.4, webrtc_sensitivity=2, 
                 min_length_of_recording=0.3, min_gap_between_recordings=0.5):
        """
        Initialize wake word enabled RealtimeSTT wrapper
        
        Args:
            model: Whisper model (tiny, base, small, medium, large)
            language: Language code (en, es, fr, etc.)
            wake_word: Wake word to activate recording
            sensitivity: Wake word detection sensitivity (0.0-1.0)
            timeout: Seconds to wait for speech after wake word
        """
        super().__init__()
        
        self.model_name = model
        self.language = language
        self.wake_word = wake_word
        self.sensitivity = sensitivity
        self.timeout = timeout
        self.post_speech_silence_duration = post_speech_silence_duration
        self.silero_sensitivity = silero_sensitivity
        self.webrtc_sensitivity = webrtc_sensitivity
        self.min_length_of_recording = min_length_of_recording
        self.min_gap_between_recordings = min_gap_between_recordings
        self.clipboard = ClipboardManager()
        
        # GUI support
        self.ui_manager = None
        self.real_time_text = ""  # For GUI display
        self.final_text = ""      # For accurate paste
        
        # Supported wake words for pvporcupine
        self.supported_wake_words = [
            'alexa', 'americano', 'blueberry', 'bumblebee', 'computer',
            'grapefruits', 'grasshopper', 'hey google', 'hey siri', 
            'jarvis', 'ok google', 'picovoice', 'porcupine', 'terminator'
        ]
        
        # Validate wake word
        if wake_word not in self.supported_wake_words:
            print(f"⚠️ Warning: '{wake_word}' not in supported list")
            print(f"Supported: {', '.join(self.supported_wake_words)}")
            print(f"Trying anyway - may work with OpenWakeWord backend")
        
        self._initialize_recorder()
        
        print(f"🎙️ Wake Word RealtimeSTT initialized")
        print(f"   Model: {model} (Whisper)")
        print(f"   Wake word: '{wake_word}'")
        print(f"   Sensitivity: {sensitivity}")
        print(f"   Timeout: {timeout}s")
    
    def _initialize_recorder(self):
        """Initialize RealtimeSTT with wake word detection"""
        try:
            # Monkey patch RealtimeSTT to fix pvporcupine access key issue
            import os
            access_key = "lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=="
            os.environ['PICOVOICE_ACCESS_KEY'] = access_key
            
            # Monkey patch pvporcupine.create to include access key
            import pvporcupine
            original_create = pvporcupine.create
            
            def patched_create(*args, **kwargs):
                if 'access_key' not in kwargs:
                    kwargs['access_key'] = access_key
                return original_create(*args, **kwargs)
            
            pvporcupine.create = patched_create
            print("🔧 Monkey patched pvporcupine.create with access key")
            
            print(f"🔍 DEBUG: Initializing AudioToTextRecorder with model='{self.model_name}'")
            self.recorder = AudioToTextRecorder(
                # Model configuration
                model=self.model_name,
                language=self.language,
                realtime_model_type=self.model_name,  # Use same model for realtime
                use_main_model_for_realtime=True,     # Force using main model
                
                # Wake word configuration  
                wake_words=self.wake_word,
                wakeword_backend='pvporcupine',  # Primary backend
                wake_words_sensitivity=self.sensitivity,
                wake_word_timeout=3,   # 3 seconds to start speaking after "jarvis"
                wake_word_activation_delay=0.0,  # Immediate wake word mode
                wake_word_buffer_duration=0.8,   # Cut out wake word from recording
                
                # Disable RealtimeSTT's console UI
                spinner=False,
                
                # Enable real-time for GUI display
                enable_realtime_transcription=False,  # Disabled for better accuracy
                on_realtime_transcription_update=self._on_realtime_update,
                on_realtime_transcription_stabilized=self._on_stabilized_update,
                
                # VAD settings from CONFIG (no more hardcoding)
                silero_sensitivity=self.silero_sensitivity,
                webrtc_sensitivity=self.webrtc_sensitivity,  
                post_speech_silence_duration=self.post_speech_silence_duration,
                min_length_of_recording=self.min_length_of_recording,
                min_gap_between_recordings=self.min_gap_between_recordings,
                
                # Pre-recording buffer
                pre_recording_buffer_duration=2.0,
                
                # Event callbacks
                on_wakeword_detected=self._on_wake_word_detected,
                on_wakeword_timeout=self._on_wake_word_timeout,
                on_wakeword_detection_start=self._on_wake_word_listening,
                on_recording_start=self._on_recording_start,
                on_recording_stop=self._on_recording_stop,
                on_vad_detect_start=self._on_vad_start,
                on_vad_detect_stop=self._on_vad_stop,
            )
            
        except Exception as e:
            print(f"❌ Error initializing pvporcupine wake word detection: {e}")
            print("❌ Wake word system requires pvporcupine with access key")
            raise  # Don't fallback, force fix the pvporcupine issue
    
    def start_listening(self):
        """Start listening for wake word + transcription"""
        print(f"👂 Listening for '{self.wake_word}'...")
        print("💡 Say your wake word, then speak your message")
        print("🛑 Press Ctrl+C to stop")
        
        try:
            while True:
                text = self.recorder.text()
                
                if text and text.strip():
                    print(f"✅ Transcribed: '{text.strip()}'")
                    
                    # Use exact same clipboard workflow as keyboard trigger
                    self.clipboard.preserve_clipboard()
                    
                    if self.clipboard.copy_to_clipboard(text):
                        print("Text copied to clipboard")
                        time.sleep(0.5)
                        
                        if self.clipboard.paste_from_clipboard():
                            print("Text pasted from clipboard")
                            time.sleep(0.5)
                            self.clipboard.restore_clipboard()
                        else:
                            print("Failed to paste - please paste manually (Cmd+V)")
                    else:
                        print("Failed to copy text to clipboard")
                    
                    return text
                else:
                    print("ℹ️ No speech detected after wake word")
                    
        except KeyboardInterrupt:
            print("\n🛑 Listening stopped by user")
            return ""
        except Exception as e:
            print(f"❌ Error during listening: {e}")
            return ""
    
    def transcribe(self, audio_data=None, language=None):
        """
        Single transcription attempt (waits for wake word + speech)
        GUI shows real-time updates, but final chunk text is pasted
        
        Args:
            audio_data: Ignored (RealtimeSTT handles capture)
            language: Optional language override
            
        Returns:
            str: Transcribed text or empty string
        """
        try:
            print(f"👂 Say '{self.wake_word}' to activate...")
            
            # GUI is already shown by _on_wake_word_detected callback
            # Real-time updates happen via _on_realtime_update callback
            
            # Get FINAL chunk transcription (accurate)
            print("🔄 Waiting for transcription to complete...")
            final_text = self.recorder.text()
            print(f"📝 Transcription received: '{final_text[:50]}...' (length: {len(final_text) if final_text else 0})")
            
            if final_text and final_text.strip():
                # Update GUI with final text and hide it
                if self.ui_manager:
                    self.ui_manager.update_transcription(final_text.strip(), is_final=True)
                    self.ui_manager.stop_recording()
                
                print(f"✅ Final transcription: '{final_text.strip()}'")
                
                # Use exact same clipboard workflow as keyboard trigger
                self.clipboard.preserve_clipboard()
                
                if self.clipboard.copy_to_clipboard(final_text.strip()):
                    print("📋 Text copied to clipboard")
                    time.sleep(0.5)
                    
                    if self.clipboard.paste_from_clipboard():
                        print("✅ Text pasted successfully")
                        time.sleep(0.5)
                        self.clipboard.restore_clipboard()
                        print("🔄 Original clipboard restored")
                    else:
                        print("❌ Failed to paste - please paste manually (Cmd+V)")
                        self.clipboard.restore_clipboard()
                else:
                    print("❌ Failed to copy text to clipboard")
                return final_text
            else:
                # Hide GUI if no speech detected
                if self.ui_manager:
                    self.ui_manager.stop_recording()
                print("ℹ️ No speech detected")
                return ""
                
        except KeyboardInterrupt:
            if self.ui_manager:
                self.ui_manager.stop_recording()
            print("🛑 Transcription interrupted")
            return ""
        except Exception as e:
            if self.ui_manager:
                self.ui_manager.stop_recording()
            print(f"❌ Transcription error: {e}")
            return ""
    
    def continuous_listen(self, max_iterations=None):
        """
        Continuous listening mode - keeps listening after each transcription
        
        Args:
            max_iterations: Maximum number of transcriptions (None = infinite)
            
        Returns:
            list: All transcribed texts
        """
        results = []
        iteration = 0
        
        print(f"🔄 Continuous listening mode activated")
        print(f"👂 Wake word: '{self.wake_word}'")
        if max_iterations:
            print(f"📊 Max iterations: {max_iterations}")
        print("🛑 Press Ctrl+C to stop")
        
        try:
            while True:
                if max_iterations and iteration >= max_iterations:
                    print(f"🏁 Reached max iterations ({max_iterations})")
                    break
                
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")
                
                text = self.transcribe()
                if text and text.strip():
                    results.append(text.strip())
                
                time.sleep(0.5)  # Brief pause between iterations
                
        except KeyboardInterrupt:
            print(f"\n🛑 Continuous listening stopped after {iteration} iterations")
        
        return results
    
    # Real-time transcription callbacks for GUI
    def _on_realtime_update(self, text):
        """Update GUI with real-time transcription"""
        self.real_time_text = text
        if self.ui_manager:
            self.ui_manager.update_transcription(text, is_final=False)
        # Real-time logging removed - you requested chunked mode only
    
    def _on_stabilized_update(self, text):
        """Update GUI with stabilized segments"""
        if self.ui_manager:
            self.ui_manager.update_transcription(text, is_final=False)
    
    # Event callback methods
    def _on_wake_word_detected(self):
        """Called when wake word is detected"""
        print("🚨 Wake word detected! Listening for speech...")
        # Show GUI when wake word detected
        if self.ui_manager:
            self.ui_manager.start_recording()
    
    def _on_wake_word_timeout(self):
        """Called when no speech follows wake word"""
        print("⏰ No speech after wake word - going back to sleep")
    
    def _on_wake_word_listening(self):
        """Called when starting to listen for wake words"""
        print(f"👂 Listening for '{self.wake_word}'...")
    
    def _on_recording_start(self):
        """Called when actual recording starts"""
        print("🔴 Recording speech...")
    
    def _on_recording_stop(self):
        """Called when recording stops"""
        print("⏹️ Recording complete - processing transcription...")
    
    def _on_vad_start(self):
        """Called when voice activity detected"""
        print("🎤 Voice detected")
    
    def _on_vad_stop(self):
        """Called when voice activity stops"""
        print("🔇 Voice stopped")
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'recorder') and self.recorder:
                print("🧹 Cleaning up wake word recorder...")
        except Exception as e:
            print(f"Warning: Cleanup error: {e}")


def test_wake_word_functionality():
    """Test the wake word wrapper"""
    print("🧪 Testing Wake Word RealtimeSTT Wrapper")
    print("=" * 40)
    
    # Test with different wake words
    test_wake_words = ['computer', 'jarvis', 'hey google']
    
    for wake_word in test_wake_words:
        print(f"\n🎯 Testing with wake word: '{wake_word}'")
        
        try:
            wrapper = WakeWordRealtimeSTTWrapper(
                model='tiny',  # Fast model for testing
                language='en',
                wake_word=wake_word,
                sensitivity=0.6,
                timeout=8.0
            )
            
            print(f"✅ Successfully initialized with '{wake_word}'")
            
            # Single transcription test
            result = wrapper.transcribe()
            if result:
                print(f"✅ Test successful: '{result}'")
            else:
                print("ℹ️ No result (timeout or no speech)")
            
            wrapper.cleanup()
            
        except Exception as e:
            print(f"❌ Test failed with '{wake_word}': {e}")
        
        # Ask if user wants to continue
        try:
            if wake_word != test_wake_words[-1]:  # Not the last one
                response = input("Try next wake word? (y/n): ").strip().lower()
                if response not in ['y', 'yes', '']:
                    break
        except KeyboardInterrupt:
            break
    
    print("\n🏁 Wake word testing complete!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            test_wake_word_functionality()
        elif sys.argv[1] == '--continuous':
            wrapper = WakeWordRealtimeSTTWrapper(
                wake_word='computer',
                sensitivity=0.6,
                timeout=8.0
            )
            try:
                wrapper.continuous_listen()
            finally:
                wrapper.cleanup()
        else:
            print("Usage: python wake_word_wrapper.py [--test|--continuous]")
    else:
        # Single use mode
        wrapper = WakeWordRealtimeSTTWrapper(
            wake_word='computer',
            sensitivity=0.6
        )
        
        try:
            wrapper.start_listening()
        finally:
            wrapper.cleanup()