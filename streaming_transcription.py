"""
Real-time streaming transcription with dual-model architecture
Fast model for immediate feedback, accurate model for final transcription
"""

import threading
import queue
import time
import numpy as np
from typing import Optional, Callable, Tuple
import pyaudio
from collections import deque


class StreamingTranscriber:
    """
    Dual-stream transcription system:
    - Stream 1: Fast (tiny model) for real-time feedback
    - Stream 2: Accurate (base model) for final transcription
    """
    
    def __init__(self, fast_model, accurate_model, 
                 on_partial_transcription: Optional[Callable] = None,
                 on_final_transcription: Optional[Callable] = None,
                 on_audio_level: Optional[Callable] = None):
        """
        Initialize streaming transcriber with two models
        
        Args:
            fast_model: Whisper tiny model for real-time
            accurate_model: Whisper base model for accuracy
            on_partial_transcription: Callback for partial results (text, is_correction)
            on_final_transcription: Callback for final results
            on_audio_level: Callback for audio visualization
        """
        self.fast_model = fast_model
        self.accurate_model = accurate_model
        
        # Callbacks
        self.on_partial_transcription = on_partial_transcription
        self.on_final_transcription = on_final_transcription
        self.on_audio_level = on_audio_level
        
        # Audio configuration
        self.sample_rate = 16000
        self.chunk_duration = 2.0  # 2 seconds per chunk for good context
        self.chunk_size = int(self.sample_rate * self.chunk_duration)
        self.frames_per_buffer = 1024
        
        # Queues for thread communication
        self.audio_queue = queue.Queue()
        self.fast_transcription_queue = queue.Queue()
        self.accurate_transcription_queue = queue.Queue()
        
        # Buffers
        self.audio_buffer = deque(maxlen=self.chunk_size * 2)  # Keep 4 seconds
        self.accumulated_text = []  # Store all transcribed segments
        self.current_segment_start = 0  # Track position in accumulated text
        
        # Threading
        self.recording = False
        self.processing = True
        self.threads = []
        
        # Audio stream
        self.p = None
        self.stream = None
        
    def start(self):
        """Start all processing threads and audio stream"""
        self.recording = True
        self.processing = True
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.frames_per_buffer
        )
        
        # Start threads
        threads = [
            threading.Thread(target=self._audio_capture_thread, daemon=True),
            threading.Thread(target=self._fast_transcription_thread, daemon=True),
            threading.Thread(target=self._accurate_transcription_thread, daemon=True),
            threading.Thread(target=self._audio_level_thread, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
            self.threads.append(thread)
            
        print("🎙️ Streaming transcription started (2 models running)")
        
    def stop(self):
        """Stop recording and wait for processing to complete"""
        self.recording = False
        
        # Wait for queues to empty
        timeout = time.time() + 5  # 5 second timeout
        while time.time() < timeout:
            if (self.audio_queue.empty() and 
                self.fast_transcription_queue.empty() and 
                self.accurate_transcription_queue.empty()):
                break
            time.sleep(0.1)
        
        self.processing = False
        
        # Clean up audio
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
            
        print("🛑 Streaming stopped")
        
    def _audio_capture_thread(self):
        """Capture audio from microphone and queue for processing"""
        audio_chunk = []
        chunk_start_time = time.time()
        
        while self.recording:
            try:
                # Read audio data
                data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Add to current chunk
                audio_chunk.extend(audio_np)
                
                # Add to rolling buffer for visualization
                self.audio_buffer.extend(audio_np)
                
                # Check if we have enough for a chunk (2 seconds)
                if len(audio_chunk) >= self.chunk_size:
                    # Queue for both transcription streams
                    chunk_array = np.array(audio_chunk[:self.chunk_size])
                    
                    # Add to both queues
                    self.fast_transcription_queue.put(chunk_array)
                    self.accurate_transcription_queue.put(chunk_array)
                    
                    # Keep last 0.5 seconds for overlap (better context)
                    overlap_size = int(self.sample_rate * 0.5)
                    audio_chunk = audio_chunk[self.chunk_size - overlap_size:]
                    
            except Exception as e:
                print(f"Audio capture error: {e}")
                
        print("Audio capture thread stopped")
        
    def _fast_transcription_thread(self):
        """Process audio with fast model for real-time feedback"""
        while self.processing:
            try:
                # Get audio chunk with timeout
                audio_chunk = self.fast_transcription_queue.get(timeout=0.5)
                
                # Transcribe with tiny model (fast)
                result = self.fast_model.transcribe(
                    audio_chunk,
                    language='en',
                    fp16=False,
                    no_speech_threshold=0.5
                )
                
                text = result['text'].strip()
                if text:
                    # Send partial transcription
                    if self.on_partial_transcription:
                        # Accumulate text
                        self.accumulated_text.append(text)
                        full_text = ' '.join(self.accumulated_text)
                        self.on_partial_transcription(full_text, False)
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Fast transcription error: {e}")
                
        print("Fast transcription thread stopped")
        
    def _accurate_transcription_thread(self):
        """Process audio with accurate model for final transcription"""
        accumulated_audio = []
        
        while self.processing:
            try:
                # Get audio chunk
                audio_chunk = self.accurate_transcription_queue.get(timeout=0.5)
                accumulated_audio.append(audio_chunk)
                
                # Process every 2 chunks (4 seconds) for better accuracy
                if len(accumulated_audio) >= 2:
                    # Combine chunks
                    combined_audio = np.concatenate(accumulated_audio)
                    
                    # Transcribe with base model (accurate)
                    result = self.accurate_model.transcribe(
                        combined_audio,
                        language='en',
                        fp16=False,
                        no_speech_threshold=0.3,
                        beam_size=5  # Better accuracy
                    )
                    
                    text = result['text'].strip()
                    if text:
                        # This is more accurate, update the display
                        if self.on_partial_transcription:
                            # Replace last segments with corrected version
                            # Keep only the accurate transcription
                            if len(self.accumulated_text) > 2:
                                # Remove last 2 fast transcriptions
                                self.accumulated_text = self.accumulated_text[:-2]
                            
                            self.accumulated_text.append(text)
                            full_text = ' '.join(self.accumulated_text)
                            self.on_partial_transcription(full_text, True)  # Mark as correction
                    
                    # Keep last chunk for context
                    accumulated_audio = accumulated_audio[-1:]
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Accurate transcription error: {e}")
                
        # Process any remaining audio
        if accumulated_audio and self.on_final_transcription:
            try:
                combined_audio = np.concatenate(accumulated_audio)
                result = self.accurate_model.transcribe(
                    combined_audio,
                    language='en',
                    fp16=False,
                    beam_size=5
                )
                final_text = ' '.join(self.accumulated_text) + ' ' + result['text'].strip()
                self.on_final_transcription(final_text.strip())
            except Exception as e:
                print(f"Final transcription error: {e}")
                
        print("Accurate transcription thread stopped")
        
    def _audio_level_thread(self):
        """Calculate and send audio levels for visualization"""
        while self.processing:
            try:
                if len(self.audio_buffer) > 1024 and self.on_audio_level:
                    # Get recent audio
                    audio_array = np.array(list(self.audio_buffer)[-4096:])
                    
                    # Send for visualization
                    self.on_audio_level(audio_array)
                    
                time.sleep(0.05)  # 20 FPS for visualization
                
            except Exception as e:
                print(f"Audio level error: {e}")
                
        print("Audio level thread stopped")
        
    def get_final_transcription(self):
        """Get the complete accumulated transcription"""
        return ' '.join(self.accumulated_text).strip()