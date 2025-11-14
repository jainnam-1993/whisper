#!/usr/bin/env python3
"""
Host-side key listener for whisper dictation.
Listens for double Right Command press to trigger transcription.
"""

# ============================================================================
# CRITICAL: Patch faster-whisper BEFORE any RealtimeSTT imports
# ============================================================================
# This monkey-patches sys.modules to intercept faster_whisper imports
# and redirect them to whisper.cpp for Metal GPU acceleration
# ============================================================================
from ..backends.whispercpp_fasterwhisper_compat import patch_realtimestt
patch_realtimestt()

# ============================================================================
# IMPORT UNIFIED CONFIGURATION
# ============================================================================
from ..config import CONFIG, BACKEND

import time
import traceback
import sys
import os
import atexit
from pynput import keyboard
from ..utils.process import SingleInstanceLock, create_daemon_thread
from ..utils.recording_events import RecordingEvent

class RealtimeSTTCommunicator:
    """RealtimeSTT backend for keyboard-triggered transcription"""

    def __init__(self, model, language, settings, backend="realtimestt"):

        try:
            from ..utils.clipboard import TranscriptionHandler, ClipboardManager

            # Select backend based on configuration
            if backend.startswith("whisper.cpp"):
                from ..backends.whispercpp_realtimestt_bridge import WhisperCppRealtimeSTTBridge
                print(f"🚀 Using whisper.cpp backend with Metal GPU acceleration")
                self.transcription_service = WhisperCppRealtimeSTTBridge(
                    model=model,
                    language=language,
                    wake_words=None,
                    config=settings
                )
            else:
                from ..backends.realtimestt_backend import RealtimeSTTWrapper
                print(f"🎙️ Using RealtimeSTT backend with faster-whisper")
                self.transcription_service = RealtimeSTTWrapper(
                    model=model,
                    language=language,
                    wake_words=None,
                    config=settings  # Pass keyboard-specific config
                )

            # Use centralized transcription handler
            clipboard = ClipboardManager()
            self.transcription_handler = TranscriptionHandler(clipboard)

        except ImportError as e:
            print(f"Error: RealtimeSTT not available: {e}")
            raise

        self.is_transcribing = False
        self.settings = settings
        self.recording_thread = None
        self.stop_requested = False

    def start_recording(self):
        """Start recording in background thread with popup"""
        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.stop_requested = False

        print("🎙️ Starting direct RealtimeSTT recording...")
        print("🔍 Press Right Command once to stop recording")

        # Show recording popup
        try:
            from ..gui.recording_popup_process import show_recording_popup
            show_recording_popup()
        except Exception as e:
            print(f"Warning: Could not show recording popup: {e}")

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

                # Hide popup when recording ends
                try:
                    from ..gui.recording_popup_process import hide_recording_popup
                    hide_recording_popup()
                except Exception as e:
                    print(f"Warning: Could not hide recording popup: {e}")

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
        # Set flag FIRST to prevent race condition with background thread
        self.stop_requested = True

        try:
            # Force immediate transcription of whatever was captured
            transcription = self.transcription_service.abort_and_transcribe()

            # Route through single transcription handler
            if transcription and transcription.strip():
                self.transcription_handler.handle_transcription(
                    transcription, "manual_stop"
                )
                print("✅ Transcription handled by stop_recording()")
            else:
                print("No speech detected yet")

            # Don't wait - we've already got the transcription
            # Just mark thread as done (it will clean up on its own)
            self.recording_thread = None

        except Exception as e:
            print(f"Error in stop_recording: {e}")
        finally:
            self.is_transcribing = False

            # Hide popup when recording stops
            try:
                from ..gui.recording_popup_process import hide_recording_popup
                hide_recording_popup()
            except Exception as e:
                print(f"Warning: Could not hide recording popup: {e}")

def create_backend(config, backend="realtimestt"):
    """Create transcription backend with keyboard settings"""
    return RealtimeSTTCommunicator(
        model=config["model_name"],
        language=config["language"],
        settings=config["keyboard_settings"],
        backend=backend
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
            print("🚀 Starting Whisper voice recognition system...")

            print("🔥 Warming up Ollama text enhancement...")

            # Warm up Ollama at startup for instant enhancement
            from ..services.text_enhancement_service import get_text_enhancement_service
            text_enhancer = get_text_enhancement_service()
            print("✅ Ollama ready for text enhancement")

            print("\n🎤 Starting key listener for double Command press...")
            print("Double-press Right Command to start recording")
            print("Single-press Right Command while recording to stop and transcribe")

            # Create shared event manager for cross-service communication
            from ..utils.recording_events import RecordingEventManager
            event_manager = RecordingEventManager()

            # Create transcription backend (whisper.cpp or RealtimeSTT)
            communicator = create_backend(CONFIG, backend=BACKEND)
            key_listener = DoubleCommandKeyListener(communicator, event_manager)

            # Register cleanup for device manager on exit
            try:
                from ..utils.audio_device_manager import cleanup_device_manager, AudioDeviceManager

                atexit.register(cleanup_device_manager)

                # Start device monitoring
                device_manager = AudioDeviceManager.get_instance()

                # Callback: clean shutdown before restart on device change
                def on_device_change_restart(device_name):
                    print(f"🔄 Audio input changed to: {device_name}")
                    print(f"🔄 Restarting service to use new device...")

                    # Clean shutdown: properly stop recorder to prevent orphaned processes
                    import time

                    try:
                        # Step 1: Shutdown recorder gracefully (lets workers exit cleanly)
                        if hasattr(communicator, 'transcription_service'):
                            service = communicator.transcription_service
                            if hasattr(service, 'recorder') and service.recorder:
                                print("🧹 Shutting down recorder...")
                                service.recorder.shutdown()
                                print("✅ Recorder shutdown complete")

                        # Step 2: Wait for workers to exit
                        time.sleep(1)
                        print("🧹 Workers cleaned up")

                        # Step 3: Stop keyboard listener to unblock main thread
                        if hasattr(device_manager, '_keyboard_listener'):
                            print("🛑 Stopping keyboard listener...")
                            device_manager._keyboard_listener.stop()

                        # Step 4: Release instance lock BEFORE exiting
                        lock.release()
                        print("🔓 Released instance lock")
                    except Exception as e:
                        print(f"⚠️ Cleanup error: {e}")

                    # Use os._exit(0) now that everything is cleaned up
                    os._exit(0)

                device_manager.register_callback(on_device_change_restart)
                device_manager.start_monitoring()
                print("✅ Device monitoring started - will restart service on device change")
            except Exception as e:
                print(f"⚠️ Failed to start device monitoring: {e}")
                import traceback
                traceback.print_exc()

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

            # Store listener reference for device change cleanup
            device_manager._keyboard_listener = listener

            listener.join()  # Keep the script running
        finally:
            # Release the lock when exiting
            lock.release()
    except Exception as e:
        print(f"Error in main function: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
