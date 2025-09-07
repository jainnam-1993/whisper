#!/usr/bin/env python3
"""
RealtimeSTT Backend Wrapper
Drop-in replacement for WhisperTranscriptionService using RealtimeSTT engine
"""

from RealtimeSTT import AudioToTextRecorder
from .transcription_base import TranscriptionService
from ..core.transcription_state import ThreadSafeTranscriptionState


class RealtimeSTTWrapper(TranscriptionService):
    """
    Drop-in replacement for WhisperTranscriptionService using RealtimeSTT backend.

    Benefits:
    - Better VAD (Voice Activity Detection)
    - Robust audio buffering and error handling
    - Same Whisper models, better architecture
    - Future-ready for real-time mode
    """

    def __init__(self, model, language, wake_words=None, config=None, **kwargs):
        """
        Initialize RealtimeSTT wrapper

        Args:
            model: Whisper model name (tiny, base, small, medium, large)
            language: Language code (en, es, fr, etc.)
            wake_words: Wake word(s) for voice activation (e.g., "jarvis")
            config: Configuration dict with all settings
            **kwargs: Backward compatibility for individual parameters
        """
        super().__init__()

        # Use config dict if provided, otherwise fall back to individual parameters
        if config:
            self.model_name = model
            self.language = language
            self.wake_words = wake_words
            self.enable_realtime = config.get("enable_realtime")
            self.pre_buffer_duration = config.get("pre_buffer_duration")
            self.vad_sensitivity = config.get("vad_sensitivity")
            self.post_speech_silence_duration = config.get("post_speech_silence_duration")  # May be None for manual mode
            self.webrtc_sensitivity = config.get("webrtc_sensitivity")
            self.min_length_of_recording = config.get("min_length_of_recording")
            self.min_gap_between_recordings = config.get("min_gap_between_recordings")
            self.wake_words_sensitivity = config.get("wake_words_sensitivity")
            self.wake_word_timeout = config.get("wake_word_timeout")
            self.wake_word_activation_delay = config.get("wake_word_activation_delay")
        else:
            # Backward compatibility - use individual parameters
            self.model_name = model
            self.language = language
            self.wake_words = wake_words
            self.enable_realtime = kwargs.get("enable_realtime")
            self.pre_buffer_duration = kwargs.get("pre_buffer_duration")
            self.vad_sensitivity = kwargs.get("vad_sensitivity")
            self.post_speech_silence_duration = kwargs.get("post_speech_silence_duration")
            self.webrtc_sensitivity = kwargs.get("webrtc_sensitivity")
            self.min_length_of_recording = kwargs.get("min_length_of_recording")
            self.min_gap_between_recordings = kwargs.get("min_gap_between_recordings")
            self.wake_words_sensitivity = kwargs.get("wake_words_sensitivity")
            self.wake_word_timeout = kwargs.get("wake_word_timeout")
            self.wake_word_activation_delay = kwargs.get("wake_word_activation_delay")

        # Unified transcription state management
        self.transcription_state = ThreadSafeTranscriptionState()

        # Initialize RealtimeSTT recorder
        self._initialize_recorder()

        wake_info = f" with wake word '{wake_words}'" if wake_words else ""
        realtime_info = " (real-time mode)" if self.enable_realtime else " (discrete mode)"
        print(f"🎙️ RealtimeSTT initialized with {model} model{wake_info}{realtime_info}")
    def _initialize_recorder(self):
        """Initialize the RealtimeSTT recorder with optimal settings"""
        try:
            # Set Picovoice access key and patch pvporcupine for RealtimeSTT compatibility
            import os
            if self.wake_words:
                os.environ['PICOVOICE_ACCESS_KEY'] = 'lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=='

                # Monkey patch pvporcupine.create to include access key
                import pvporcupine
                original_create = pvporcupine.create

                def patched_create(*args, **kwargs):
                    # Always add access_key as first argument if not present
                    if len(args) == 0 or 'access_key' not in kwargs:
                        return original_create('lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w==', *args, **kwargs)
                    else:
                        return original_create(*args, **kwargs)

                pvporcupine.create = patched_create

            # Base configuration
            config = {
                # Model configuration - same as your current setup
                "model": self.model_name,
                "language": self.language,
                "realtime_model_type": self.model_name,  # Use same model for realtime
                "use_main_model_for_realtime": True,     # Force using main model

                # Real-time mode configuration - only enable if explicitly requested
                "enable_realtime_transcription": self.enable_realtime,

                # Wake word configuration - pvporcupine with continuous listening
                "wake_words": "jarvis" if self.wake_words else None,
                "wakeword_backend": "pvporcupine" if self.wake_words else None,
                "wake_words_sensitivity": self.wake_words_sensitivity,  # From CONFIG
                "wake_word_timeout": self.wake_word_timeout,  # From CONFIG  
                "wake_word_activation_delay": self.wake_word_activation_delay,  # From CONFIG

                # Disable RealtimeSTT's console UI (we handle UI)
                "spinner": False,

                # VAD configuration - use settings from config
                "silero_sensitivity": self.vad_sensitivity,   # Voice activity detection sensitivity
                "webrtc_sensitivity": self.webrtc_sensitivity, # Alternative VAD method

                # Recording behavior - conditional silence detection
                "post_speech_silence_duration": self.post_speech_silence_duration if self.post_speech_silence_duration is not None else 999.0,  # Use 999s for manual mode (effectively infinite)
                "min_length_of_recording": self.min_length_of_recording,       # From CONFIG
                "min_gap_between_recordings": self.min_gap_between_recordings,      # From CONFIG

                # Pre-recording buffer (captures audio before VAD triggers)
                "pre_recording_buffer_duration": self.pre_buffer_duration,

                # Callbacks for integration (including real-time transcription)
                "on_recording_start": self._on_recording_start,
                "on_recording_stop": self._on_recording_stop,
                "on_vad_detect_start": self._on_vad_start,
                "on_vad_detect_stop": self._on_vad_stop,
                "on_realtime_transcription_update": self._on_realtime_update,
                "on_realtime_transcription_stabilized": self._on_realtime_stabilized,
            }

            # Remove None values (wake_words parameter only added if specified)
            config = {k: v for k, v in config.items() if v is not None}

            # Debug: Check if environment variable is set
            import os
            if self.wake_words:
                env_key = os.environ.get('PICOVOICE_ACCESS_KEY')
                print(f"🔍 DEBUG: PICOVOICE_ACCESS_KEY in environment: {'✅ Yes' if env_key else '❌ No'}")
                if env_key:
                    print(f"🔍 DEBUG: Key starts with: {env_key[:10]}...")
                print(f"🔍 DEBUG: Wake word config: backend={config.get('wakeword_backend')}, words={config.get('wake_words')}")

            self.recorder = AudioToTextRecorder(**config)

            if self.wake_words:
                print("🔍 DEBUG: AudioToTextRecorder created successfully with wake word config")

        except Exception as e:
            print(f"Error initializing RealtimeSTT: {e}")
            import traceback
            traceback.print_exc()
            raise
        

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

            # Clear previous transcription state
            self.transcription_state.clear()

            # Check if we're in manual mode (no silence duration = keyboard mode)
            if self.post_speech_silence_duration is None:
                # Manual mode - we control start/stop, no VAD
                print("🎯 Using manual recording mode (no VAD)")
                self.recorder.start()
                # In keyboard mode, this will be stopped by abort_and_transcribe()
                # We block here until manually stopped
                import time
                while True:
                    time.sleep(0.1)  # Keep alive until abort_and_transcribe() is called
            else:
                # Automatic mode - RealtimeSTT handles all the audio capture and processing with VAD
                text = self.recorder.text()

                if text and text.strip():
                    print(f"✅ Complete transcription: '{text}'")
                    self.transcription_state.update_text(text, is_final=True)
                    return text
                else:
                    # Check for best available text from state
                    best_text = self.transcription_state.get_best_text()
                    if best_text:
                        state = self.transcription_state.get_state()
                        if state.is_stable:
                            print(f"🔄 Using stabilized transcription: '{best_text}'")
                        else:
                            print(f"⚡ Using partial transcription: '{best_text}'")
                        return best_text
                    else:
                        print("ℹ️ No speech detected")
                        return ""

        except KeyboardInterrupt:
            print("🛑 Recording interrupted by user")
            # Return best available text when interrupted
            best_text = self.transcription_state.get_best_text()
            if best_text:
                print(f"⚡ Returning text from interrupt: '{best_text}'")
                return best_text
            return ""
        except Exception as e:
            print(f"❌ RealtimeSTT transcription error: {e}")
            return ""

    def abort_and_transcribe(self):
        """Unified transcription method using official stop() + text() pattern"""
        try:
            if hasattr(self, 'recorder') and self.recorder:
                print("🛑 Stopping RealtimeSTT recorder...")
                
                # Use unified approach: stop with backdate trimming + direct text retrieval
                # Use min_length_of_recording from settings as backdate trim duration
                trim_duration = self.settings.get('min_length_of_recording', 0.3)
                self.recorder.stop(backdate_stop_seconds=trim_duration, backdate_resume_seconds=trim_duration)
                text = self.recorder.text()
                print("✅ RealtimeSTT recorder stopped successfully")
                
                if text and text.strip():
                    print(f"⚡ Transcription: '{text}'")
                    return text.strip()
                else:
                    print("⏹️ No transcription available - recording may have been too short")
                    return ""
        except Exception as e:
            print(f"❌ Error in abort_and_transcribe: {e}")
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

    def _on_realtime_update(self, text):
        """Called with partial transcription updates"""
        self.transcription_state.update_text(text, is_final=False, is_stable=False)
        # Only show real-time updates if real-time mode is enabled
        if self.enable_realtime:
            print(f"🔄 Partial: {text}")

    def _on_realtime_stabilized(self, text):
        """Called when transcription segment is stabilized"""
        self.transcription_state.update_text(text, is_final=False, is_stable=True)
        # Only show stabilized updates if real-time mode is enabled
        if self.enable_realtime:
            print(f"✅ Stable: {text}")

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

# Duplicate method removed - consolidated above


def create_transcription_service(model_name, language=None):
    """
    Factory function to create RealtimeSTT transcription service

    Args:
        model_name: Whisper model (tiny, base, small, medium, large)
        language: Language code

    Returns:
        RealtimeSTTWrapper instance
    """
    return RealtimeSTTWrapper(model=model_name, language=language)


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
