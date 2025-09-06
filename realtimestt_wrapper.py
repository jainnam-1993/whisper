#!/usr/bin/env python3
"""
RealtimeSTT Backend Wrapper
Drop-in replacement for WhisperTranscriptionService using RealtimeSTT engine
"""

from RealtimeSTT import AudioToTextRecorder
from transcription_service import TranscriptionService


class RealtimeSTTWrapper(TranscriptionService):
    """
    Drop-in replacement for WhisperTranscriptionService using RealtimeSTT backend.
    
    Benefits:
    - Better VAD (Voice Activity Detection)
    - Robust audio buffering and error handling  
    - Same Whisper models, better architecture
    - Future-ready for real-time mode
    """
    
    def __init__(self, model="base", language="en"):
        """
        Initialize RealtimeSTT wrapper
        
        Args:
            model: Whisper model name (tiny, base, small, medium, large)
            language: Language code (en, es, fr, etc.)
        """
        super().__init__()
        
        # Store config
        self.model_name = model
        self.language = language
        
        # Initialize RealtimeSTT recorder
        self._initialize_recorder()
        
        print(f"🎙️ RealtimeSTT initialized with {model} model")
    
    def _initialize_recorder(self):
        """Initialize the RealtimeSTT recorder with optimal settings"""
        try:
            self.recorder = AudioToTextRecorder(
                # Model configuration - same as your current setup
                model=self.model_name,
                language=self.language,
                
                # Discrete mode (like your current workflow)
                enable_realtime_transcription=False,
                
                # Disable RealtimeSTT's console UI (we handle UI)
                spinner=False,
                
                # VAD configuration - optimized for discrete recording
                silero_sensitivity=0.4,  # Voice activity detection sensitivity
                webrtc_sensitivity=3,    # Alternative VAD method
                
                # Recording behavior
                post_speech_silence_duration=0.4,  # Stop after 400ms silence
                min_length_of_recording=0.3,       # Minimum 300ms recording
                min_gap_between_recordings=0,      # No gap between recordings
                
                # Pre-recording buffer (captures audio before VAD triggers)
                pre_recording_buffer_duration=1.0,  # 1 second pre-buffer
                
                # Audio processing (removed incompatible parameters)
                
                # Callbacks for integration (optional)
                on_recording_start=self._on_recording_start,
                on_recording_stop=self._on_recording_stop,
                on_vad_detect_start=self._on_vad_start,
                on_vad_detect_stop=self._on_vad_stop,
            )
            
        except Exception as e:
            print(f"Error initializing RealtimeSTT: {e}")
            print("Falling back to basic configuration...")
            
            # Fallback with minimal configuration
            self.recorder = AudioToTextRecorder(
                model=self.model_name,
                language=self.language,
                spinner=False
            )
    
    def transcribe(self, audio_data=None, language=None):
        """
        Transcribe audio using RealtimeSTT backend
        
        Args:
            audio_data: Ignored (RealtimeSTT handles audio capture)
            language: Optional language override
            
        Returns:
            str: Transcribed text
        """
        try:
            print("📻 Starting recording with RealtimeSTT...")
            
            # RealtimeSTT handles all the audio capture and processing
            text = self.recorder.text()
            
            if text and text.strip():
                print(f"✅ Transcribed: '{text}'")
                # Use inherited type_text method for output
                self.type_text(text)
                return text
            else:
                print("ℹ️ No speech detected")
                return ""
                
        except KeyboardInterrupt:
            print("🛑 Recording interrupted by user")
            return ""
        except Exception as e:
            print(f"❌ RealtimeSTT transcription error: {e}")
            return ""
    
    def cleanup(self):
        """Clean up RealtimeSTT resources"""
        try:
            if hasattr(self, 'recorder') and self.recorder:
                # RealtimeSTT handles its own cleanup
                print("🧹 RealtimeSTT cleanup complete")
        except Exception as e:
            print(f"Warning: RealtimeSTT cleanup error: {e}")
    
    # Optional callback methods for debugging/integration
    def _on_recording_start(self):
        """Called when recording starts"""
        print("🔴 RealtimeSTT: Recording started")
    
    def _on_recording_stop(self):
        """Called when recording stops"""  
        print("⏹️ RealtimeSTT: Recording stopped")
    
    def _on_vad_start(self):
        """Called when voice activity detected"""
        print("🎤 RealtimeSTT: Voice detected")
    
    def _on_vad_stop(self):
        """Called when voice activity stops"""
        print("🔇 RealtimeSTT: Voice stopped")
    
    def enable_realtime_mode(self):
        """Enable real-time transcription mode (future enhancement)"""
        print("🚀 Enabling real-time mode...")
        
        # Reinitialize with real-time enabled
        self.recorder = AudioToTextRecorder(
            model=self.model_name,
            language=self.language,
            enable_realtime_transcription=True,
            realtime_processing_pause=0.2,  # 200ms chunks
            spinner=False,
            on_realtime_transcription_update=self._on_realtime_update
        )
        
        print("✅ Real-time mode enabled")
    
    def _on_realtime_update(self, text):
        """Handle real-time transcription updates (future enhancement)"""
        print(f"📝 Real-time: {text}")
        # Future: Send to UI for real-time display


def create_transcription_service(model_name, language=None, use_realtimestt=False):
    """
    Factory function to create transcription service
    
    Args:
        model_name: Whisper model (tiny, base, small, medium, large)
        language: Language code
        use_realtimestt: Use RealtimeSTT backend (recommended)
        
    Returns:
        TranscriptionService instance
    """
    if use_realtimestt:
        return RealtimeSTTWrapper(model=model_name, language=language)
    else:
        # Fallback to existing WhisperTranscriptionService
        from transcription_service import WhisperTranscriptionService
        import whisper
        
        model = whisper.load_model(model_name)
        return WhisperTranscriptionService(model)


if __name__ == "__main__":
    # Test the wrapper
    print("Testing RealtimeSTT Wrapper...")
    
    wrapper = RealtimeSTTWrapper(model="tiny", language="en")
    
    print("Say something (press Ctrl+C to stop):")
    try:
        text = wrapper.transcribe()
        print(f"Final result: {text}")
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    finally:
        wrapper.cleanup()