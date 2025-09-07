#!/usr/bin/env python3
"""
Enhanced RealtimeSTT Wrapper with Wake Word Support
Extends the basic RealtimeSTT wrapper to include voice activation capabilities
"""

from RealtimeSTT import AudioToTextRecorder
from ..backends.transcription_base import TranscriptionService
from ..utils.clipboard import ClipboardManager
from ..utils.recording_events import RecordingEvent
import time
import threading


# ClipboardManager moved to src/utils/clipboard.py


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
                 min_length_of_recording=0.3, min_gap_between_recordings=0.5,
                 event_manager=None):
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
        

        
        # Event system for manual stop capability
        self.event_manager = event_manager
        self.manual_stop_requested = False
        self.stop_event = threading.Event()
        
        # Subscribe to manual stop events if event manager provided
        if self.event_manager:
            self.event_manager.subscribe(RecordingEvent.MANUAL_STOP_REQUESTED, self._on_manual_stop_requested)
        
        # Transcription buffer for manual stop scenarios
        self.last_transcription = ""  # Store transcription from callbacks
        self.transcription_buffer = []  # Store all chunks for manual stop
        
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
                    
                    # Use unified clipboard workflow
                    if self.clipboard.copy_and_paste_text(text):
                        print("Text successfully copied and pasted")
                    else:
                        print("Failed to copy/paste - please paste manually (Cmd+V)")
                    
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
            
            # Reset manual stop state
            self.manual_stop_requested = False
            self.stop_event.clear()
            
            # Clear transcription buffers for new recording
            self.last_transcription = ""
            self.transcription_buffer = []
            
            # Notify that wake word recording started
            if self.event_manager:
                self.event_manager.emit(RecordingEvent.WAKE_WORD_RECORDING_STARTED)
            
            # Check if manual stop was requested while we were starting
            if self.stop_event.wait(timeout=0.1):
                print("⚡ Manual stop detected immediately - aborting...")
                final_text = self.abort_recording()
            else:
                # Normal flow - let recorder.text() handle VAD naturally
                print("🔄 Starting normal transcription (with VAD silence detection)...")
                try:
                    final_text = self.recorder.text()
                    print(f"🔄 Normal transcription completed: '{final_text[:50] if final_text else 'None'}...'")
                except Exception as e:
                    print(f"❌ Normal transcription error: {e}")
                    final_text = ""
            
            print(f"📝 Final transcription for processing: '{final_text[:50] if final_text else 'None'}...' (length: {len(final_text) if final_text else 0})")
            
            # Use unified processing for both completion paths
            result = self._process_final_text(final_text)
            print(f"🔄 _process_final_text returned: '{result[:50] if result else 'None'}...'")
            return result
                
        except KeyboardInterrupt:

            print("🛑 Transcription interrupted")
            return ""
        except Exception as e:

            print(f"❌ Transcription error: {e}")
            import traceback
            traceback.print_exc()
            return ""
        finally:
            # Always notify that wake word recording stopped
            if self.event_manager:
                self.event_manager.emit(RecordingEvent.WAKE_WORD_RECORDING_STOPPED)
    
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
        """Real-time transcription callback - not used in chunk mode"""
        # Real-time logging removed - using chunked mode only
        pass
    
    def _on_stabilized_update(self, text):
        """Store stabilized segments for manual stop scenario"""
        if text and text.strip():
            # Store for manual stop scenario
            self.transcription_buffer.append(text.strip())
            self.last_transcription = " ".join(self.transcription_buffer)
    
    # Event callback methods
    def _on_wake_word_detected(self):
        """Called when wake word is detected"""
        print("🚨 Wake word detected! Listening for speech...")

    
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

    
    def _on_manual_stop_requested(self):
        """Called when manual stop is requested via keyboard"""
        print("⚡ Manual stop requested - forcing immediate transcription...")
        self.manual_stop_requested = True
        self.stop_event.set()

    
    def _process_final_text(self, text):
        """Unified text processing for both normal and manual completion"""
        if text and text.strip():

            
            print(f"✅ Final transcription: '{text.strip()}'")
            
            # Use unified clipboard workflow (same as manual trigger mode)
            if self.clipboard.copy_and_paste_text(text.strip()):
                print("✅ Text successfully copied and pasted")
            else:
                print("❌ Failed to copy/paste - please paste manually (Cmd+V)")
                
            return text
        else:
            # Hide GUI if no speech detected

            print("ℹ️ No speech detected")
            return ""
    
    def abort_recording(self):
        """Stop recording and return any captured text"""
        try:
            print("🛑 Aborting recording...")
            if hasattr(self, 'recorder') and self.recorder:
                # Use abort() to stop immediately without waiting
                if hasattr(self.recorder, 'abort'):
                    self.recorder.abort()
                    print("✅ Recorder aborted")
                elif hasattr(self.recorder, 'stop'):
                    self.recorder.stop()
                    print("✅ Recorder stopped")
                
                # Return accumulated transcription from callbacks
                result = self.last_transcription
                
                # Clear for next use
                self.last_transcription = ""
                self.transcription_buffer = []
                
                if result:
                    print(f"📝 Returning captured text: '{result[:50]}...'")
                    return result
                else:
                    print("ℹ️ No text captured before abort")
                    return ""
                    
        except Exception as e:
            print(f"❌ Error in abort_recording: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
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