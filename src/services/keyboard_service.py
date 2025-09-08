#!/usr/bin/env python3
"""
Host-side key listener for whisper dictation.
Listens for double Right Command press to trigger transcription.
"""

# Configuration - Change backend here (no code deletion)
CONFIG = {
    "transcription_backend": "realtimestt",  # Only RealtimeSTT supported
    "model_name": "medium",
    "language": "en",


    # Double command key specific settings (manual control)
    "keyboard_settings": {
        "enable_realtime": False,
        "pre_buffer_duration": 1.5,
        "vad_sensitivity": 0.3,
        "post_speech_silence_duration": None,  # Explicit None for manual control
        "webrtc_sensitivity": 2,
        "min_length_of_recording": 0.3,
        "min_gap_between_recordings": 0.5
    }
}

import time
import traceback
import sys
from pynput import keyboard
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
            from ..utils.clipboard import TranscriptionHandler, ClipboardManager

            # For keyboard trigger: use direct recording
            self.transcription_service = RealtimeSTTWrapper(
                model=model,
                language=language,
                wake_words=None,
                config=settings.get('keyboard_settings', {})  # Pass keyboard-specific config
            )

            # Use centralized transcription handler
            clipboard = ClipboardManager()
            self.transcription_handler = TranscriptionHandler(clipboard)

        except ImportError as e:
            print(f"Error: RealtimeSTT not available: {e}")
            raise

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

                # Process transcription through single handler - NO race conditions
                if self.stop_requested:
                    # If stop was requested, transcription was already handled in stop_recording()
                    print("⏭️ Transcription already handled by stop_recording()")
                elif transcription and transcription.strip():
                    # Route through single transcription handler
                    self.transcription_handler.handle_transcription(
                        transcription, "manual_background"
                    )
                else:
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

            # Route through single transcription handler
            if transcription and transcription.strip():
                self.transcription_handler.handle_transcription(
                    transcription, "manual_stop"
                )
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

                # Priority 1: Check for double-click to start recording
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

                # Priority 3: Single press with no active recording - just update timestamp
                else:
                    print("⏸️ Single press - waiting for double-click...")

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

            # DISABLED: Wake word listener (keeping only double command for simplicity)
            # wake_word_thread = None
            # if CONFIG.get("wake_word_settings", {}).get("wake_words"):
            #     print("🎤 Starting parallel wake word listener for 'Jarvis'...")
            #     # (wake word code commented out for simplicity)
            print("🎯 SIMPLIFIED: Only double Right Command recording active")


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
