#!/usr/bin/env python3
"""
Host-side key listener for whisper dictation.
Listens for double Right Command press to trigger transcription.
"""

# Configuration - Change backend here (no code deletion)
CONFIG = {
    "transcription_backend": "realtimestt",  # Only RealtimeSTT supported
    "model_name": "base",
    "language": "en",
    
    # Wake word specific settings (automatic control)
    "wake_word_settings": {
        "enable_realtime": False,
        "pre_buffer_duration": 1.5,
        "vad_sensitivity": 0.3,
        "post_speech_silence_duration": 1.5,        # Auto-stop after 1.5s silence
        "webrtc_sensitivity": 2,
        "min_length_of_recording": 0.3,
        "min_gap_between_recordings": 0.5,
        "wake_words": "jarvis",
        "wake_words_sensitivity": 1.0,
        "wake_word_timeout": 3,
        "wake_word_activation_delay": 0.0
    },
    
    # Double command key specific settings (manual control)
    "keyboard_settings": {
        "enable_realtime": False,
        "pre_buffer_duration": 1.5,
        "vad_sensitivity": 0.3,
        "post_speech_silence_duration": None,  # Explicit None for manual control
        "webrtc_sensitivity": 2,
        "min_length_of_recording": 0.3,
        "min_gap_between_recordings": 0.5
        # No wake word settings for keyboard trigger
    }
}

import time
import traceback
import sys
from pynput import keyboard
from ..utils.clipboard import ClipboardManager
from ..utils.process import SingleInstanceLock, create_daemon_thread
from ..utils.recording_events import RecordingEvent

# SingleInstanceLock moved to src/utils/process.py

# ClipboardManager moved to src/utils/clipboard.py

class RealtimeSTTCommunicator:
    """RealtimeSTT backend for keyboard-triggered transcription"""

    def __init__(self, model="base", language="en", settings=None):
        settings = settings or {}
        try:
            from ..backends.realtimestt_backend import RealtimeSTTWrapper
            # For keyboard trigger: use direct recording (no wake words)
            self.transcription_service = RealtimeSTTWrapper(
                model=model,
                language=language,
                wake_words=None,  # Force no wake words for keyboard trigger
                config=settings  # Pass entire config dict
            )
        except ImportError as e:
            print(f"Error: RealtimeSTT not available: {e}")
            raise

        self.clipboard = ClipboardManager()  # Use shared clipboard manager
        self.is_transcribing = False
        self.settings = settings or {}
        self.recording_thread = None
        self.stop_requested = False

    def start_recording(self):
        """Start recording in background thread"""
        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.stop_requested = False

        print("🎙️ Starting direct RealtimeSTT recording...")
        print("🔍 Press Right Command once to stop recording")

        # Store start time for compatibility with original pattern
        self.start_time = time.time()

        # Start recording in background thread (like original subprocess)
        def record_in_background():
            try:
                # This will block until speech is detected and completed
                # The stop_recording() method can interrupt it with abort()
                transcription = self.transcription_service.transcribe()

                # Process transcription whether stopped early or completed naturally
                if self.stop_requested:
                    # If stop was requested, transcription was already handled in stop_recording()
                    print("⏭️ Transcription already handled by stop_recording()")
                elif transcription and transcription.strip():
                    print(f"Transcription completed: {transcription}")

                    # Use unified clipboard workflow
                    if self.clipboard.copy_and_paste_text(transcription):
                        print("Text successfully copied and pasted")
                    else:
                        print("Failed to copy/paste - please paste manually (Cmd+V)")
                elif not transcription or not transcription.strip():
                    print("No speech detected")

            except Exception as e:
                if not self.stop_requested:
                    print(f"RealtimeSTT recording error: {e}")
            finally:
                self.is_transcribing = False

        # Start recording in background (like original subprocess.Popen)
        self.recording_thread = create_daemon_thread(
            target=record_in_background,
            name="RealtimeSTT-Recording"
        )
        self.recording_thread.start()

    def stop_recording(self):
        """Stop recording and transcribe immediately"""
        if not self.is_transcribing:
            return

        print("🛑 Stop requested - forcing immediate transcription...")
        self.stop_requested = True

        try:
            # Force immediate transcription of whatever was captured
            transcription = self.transcription_service.abort_and_transcribe()
            
            # Process transcription immediately
            if transcription and transcription.strip():
                print(f"Transcription from manual stop: {transcription}")
                # Paste here since we're aborting the background thread
                if self.clipboard.copy_and_paste_text(transcription):
                    print("Text successfully copied and pasted")
                else:
                    print("Failed to copy/paste - please paste manually (Cmd+V)")
            else:
                print("No speech detected yet")

            # Don't wait - we've already got the transcription
            # Just mark thread as done (it will clean up on its own)
            self.recording_thread = None

        except Exception as e:
            print(f"Error in stop_recording: {e}")
        finally:
            self.is_transcribing = False

def create_backend(config):
    """Create RealtimeSTT backend with keyboard settings"""
    keyboard_settings = config.get("keyboard_settings", {})
    
    return RealtimeSTTCommunicator(
        model=config.get("model_name", "base"),
        language=config.get("language", "en"),
        settings=keyboard_settings
    )

# DockerCommunicator removed - using RealtimeSTT only

class DoubleCommandKeyListener:
    def __init__(self, docker_communicator, event_manager=None):
        self.communicator = docker_communicator
        self.event_manager = event_manager
        self.key = keyboard.Key.cmd_r
        self.last_press_time = 0  # Initialize to 0

    def on_key_press(self, key):
        try:
            # Debug: Log all right command key presses
            if key == self.key:
                print(f"🔍 DEBUG: Right Command key pressed at {time.time()}")
                
            if key == self.key:
                current_time = time.time()
                # Calculate time difference from last press
                time_diff = current_time - self.last_press_time if self.last_press_time > 0 else 999

                print(f"🔍 DEBUG: Time since last press: {time_diff:.3f}s, is_transcribing: {self.communicator.is_transcribing}")

                # Priority 1: Check for double-click FIRST (before wake word check)
                if 0 < time_diff < 2.0 and not self.communicator.is_transcribing:
                    print("✅ Double command detected - starting manual recording!")
                    if self.event_manager:
                        self.event_manager.emit(RecordingEvent.MANUAL_RECORDING_STARTED)
                    self.communicator.start_recording()
                    
                # Priority 2: If manual recording is active, stop it
                elif self.communicator.is_transcribing:
                    print("🛑 Manual recording active - stopping recording")
                    if self.event_manager:
                        self.event_manager.emit(RecordingEvent.MANUAL_RECORDING_STOPPED)
                    self.communicator.stop_recording()
                    
                # Priority 3: If wake word is recording, stop it (only if not double-click)
                elif self.event_manager and self.event_manager.is_wake_word_recording():
                    print("🎤 Wake word recording active - single press will stop recording")
                    self.event_manager.emit(RecordingEvent.MANUAL_STOP_REQUESTED)
                    
                # Priority 4: Single press with no active recording - just update timestamp
                else:
                    print("⏸️ Single press - waiting for double-click or wake word...")

                self.last_press_time = current_time
        except Exception as e:
            print(f"Error in key press handler: {e}")
            traceback.print_exc()

    def on_key_release(self, key):
        pass

# check_docker_container removed - using RealtimeSTT only

def main():
    try:
        # Create a single instance lock
        lock = SingleInstanceLock()
        if not lock.acquire():
            print("Another instance is already running. Exiting.")
            sys.exit(1)

        try:
            print("Starting key listener for double Command press...")
            print("Double-press Right Command to start recording")
            print("Single-press Right Command while recording to stop and transcribe")

            # Create shared event manager for cross-service communication
            from ..utils.recording_events import RecordingEventManager
            event_manager = RecordingEventManager()

            # Create RealtimeSTT backend
            communicator = create_backend(CONFIG)
            key_listener = DoubleCommandKeyListener(communicator, event_manager)

            # Start wake word listener in parallel thread if configured
            wake_word_thread = None
            if CONFIG.get("wake_word_settings", {}).get("wake_words"):
                print("🎤 Starting parallel wake word listener for 'Jarvis'...")
                def run_wake_word_listener():
                    try:
                        from .wake_word_service import WakeWordRealtimeSTTWrapper

                        # Get wake word settings
                        wake_settings = CONFIG["wake_word_settings"]

                        # Create wake word wrapper with event manager
                        wrapper = WakeWordRealtimeSTTWrapper(
                            model=CONFIG.get("model_name", "base"),
                            language=CONFIG.get("language", "en"),
                            wake_word="jarvis",
                            sensitivity=wake_settings["wake_words_sensitivity"],
                            timeout=wake_settings["wake_word_timeout"],
                            post_speech_silence_duration=wake_settings["post_speech_silence_duration"],
                            silero_sensitivity=wake_settings["vad_sensitivity"],
                            webrtc_sensitivity=wake_settings["webrtc_sensitivity"],
                            min_length_of_recording=wake_settings["min_length_of_recording"],
                            min_gap_between_recordings=wake_settings["min_gap_between_recordings"],
                            event_manager=event_manager
                        )

                        # Start continuous listening with GUI support
                        wrapper.continuous_listen()
                    except Exception as e:
                        print(f"Wake word listener error: {e}")

                wake_word_thread = create_daemon_thread(
                    target=run_wake_word_listener,
                    name="WakeWord-Listener"
                )
                wake_word_thread.start()
                print("✅ Wake word listener started in background with GUI support")
                print("🎯 NEW: Say 'jarvis' then hit Right Command to stop recording!")

            # Start the keyboard listener
            listener = keyboard.Listener(
                on_press=key_listener.on_key_press,
                on_release=key_listener.on_key_release
            )
            listener.start()
            listener.join()  # Keep the script running
        finally:
            # Release the lock when exiting
            lock.release()
    except Exception as e:
        print(f"Error in main function: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
