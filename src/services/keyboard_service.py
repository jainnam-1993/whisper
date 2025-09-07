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
        "post_speech_silence_duration": 3.0,        # Auto-stop after 3s silence
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
        # NO post_speech_silence_duration - manual control only
        "webrtc_sensitivity": 2,
        "min_length_of_recording": 0.3,
        "min_gap_between_recordings": 0.5
        # No wake word settings for keyboard trigger
    }
}

import time
import os
import subprocess
import threading
import traceback
import sys
import fcntl
from pynput import keyboard
from ..utils.accessibility import _execute_applescript_safely

class SingleInstanceLock:
    """Ensures only one instance of the application runs at a time"""

    def __init__(self, lock_file_path=None):
        self.lock_file_path = lock_file_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '.host_key_listener.lock'
        )
        self.lock_file = None

    def acquire(self):
        """Try to acquire the lock. Return True if successful, False otherwise."""
        try:
            self.lock_file = open(self.lock_file_path, 'w')
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write PID to the lock file
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            return True
        except IOError:
            # Another instance has the lock
            if self.lock_file:
                self.lock_file.close()
            return False

    def release(self):
        """Release the lock"""
        if self.lock_file:
            fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
            try:
                os.unlink(self.lock_file_path)
            except:
                pass

class ClipboardManager:
    """Handles copying text to clipboard with preservation support"""

    def __init__(self):
        self.preserved_content = None

    def preserve_clipboard(self):
        """Preserve current clipboard content"""
        try:
            result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
            self.preserved_content = result.stdout
            print(f"Preserved clipboard content ({len(self.preserved_content)} chars)")
            return True
        except Exception as e:
            print(f"Warning: Could not preserve clipboard: {e}")
            self.preserved_content = None
            return False

    def restore_clipboard(self):
        """Restore previously preserved clipboard content"""
        if self.preserved_content is not None:
            try:
                process = subprocess.Popen(
                    ['pbcopy'],
                    stdin=subprocess.PIPE,
                    close_fds=True
                )
                process.communicate(input=self.preserved_content.encode('utf-8'))
                print(f"✓ Restored original clipboard content ({len(self.preserved_content)} chars)")
                return True
            except Exception as e:
                print(f"Warning: Could not restore clipboard: {e}")
                return False
        else:
            print("No preserved clipboard content to restore")
            return False

    @staticmethod
    def copy_to_clipboard(text):
        try:
            # Use pbcopy on macOS
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                close_fds=True
            )
            process.communicate(input=text.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def paste_from_clipboard_applescript():
        """Uses AppleScript to paste from clipboard - more reliable on macOS"""
        try:
            print("Attempting to paste with AppleScript...")
            # Create AppleScript to paste content from clipboard
            applescript = '''
            try
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    log "Current frontmost app: " & frontApp
                    keystroke "v" using command down
                    return "success"
                end tell
            on error errMsg
                log "Error in AppleScript: " & errMsg
                return "error: " & errMsg
            end try
            '''

            # Execute the AppleScript securely
            result = _execute_applescript_safely(applescript, timeout=5)
            print(f"AppleScript result: stdout={result.stdout.strip()}, stderr={result.stderr.strip()}")

            if result.returncode == 0 and "error:" not in result.stdout:
                print("AppleScript paste seems successful")
                return True
            else:
                print(f"AppleScript paste failed: {result.stderr or result.stdout}")
                return False
        except (RuntimeError, ValueError) as e:
            print(f"Secure AppleScript execution failed: {e}")
            return False
        except Exception as e:
            print(f"Error pasting with AppleScript: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def paste_from_clipboard():
        """First tries AppleScript, then falls back to keyboard simulation"""
        # Try AppleScript first
        if ClipboardManager.paste_from_clipboard_applescript():
            return True

        # Fallback to keyboard simulation
        try:
            # Use keyboard shortcut to paste
            keyboard_controller = keyboard.Controller()
            with keyboard_controller.pressed(keyboard.Key.cmd):
                keyboard_controller.press('v')
                keyboard_controller.release('v')
            return True
        except Exception as e:
            print(f"Error pasting from clipboard: {e}")
            traceback.print_exc()
            return False

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

        self.clipboard = ClipboardManager()  # Reuse existing clipboard manager
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
                if transcription and transcription.strip():
                    print(f"Transcription completed: {transcription}")

                    # Copy and paste transcription
                    self.clipboard.preserve_clipboard()

                    if self.clipboard.copy_to_clipboard(transcription):
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
                elif not transcription or not transcription.strip():
                    print("No speech detected")

            except Exception as e:
                if not self.stop_requested:
                    print(f"RealtimeSTT recording error: {e}")
            finally:
                self.is_transcribing = False

        # Start recording in background (like original subprocess.Popen)
        self.recording_thread = threading.Thread(target=record_in_background, daemon=True)
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

                # Copy and paste transcription
                self.clipboard.preserve_clipboard()

                if self.clipboard.copy_to_clipboard(transcription):
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
            else:
                print("No speech detected yet")

            # Wait for background thread to finish naturally (brief timeout)
            if self.recording_thread and self.recording_thread.is_alive():
                print("⏳ Waiting for recording thread to finish...")
                self.recording_thread.join(timeout=1.0)

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
    def __init__(self, docker_communicator):
        self.communicator = docker_communicator
        self.key = keyboard.Key.cmd_r
        self.last_press_time = 0

    def on_key_press(self, key):
        try:
            # Debug: Log all right command key presses
            if key == self.key:
                print(f"🔍 DEBUG: Right Command key pressed at {time.time()}")
            if key == self.key:
                current_time = time.time()
                time_diff = current_time - self.last_press_time

                print(f"🔍 DEBUG: Time since last press: {time_diff:.3f}s, is_transcribing: {self.communicator.is_transcribing}")

                # If not recording and double-pressed (within 0.5 seconds)
                if not self.communicator.is_transcribing and time_diff < 2.0 and time_diff > 0:
                    print("✅ Double command detected - starting recording!")
                    self.communicator.start_recording()
                # If recording and single pressed - stop recording
                elif self.communicator.is_transcribing:
                    self.communicator.stop_recording()

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

            # Create RealtimeSTT backend
            communicator = create_backend(CONFIG)
            key_listener = DoubleCommandKeyListener(communicator)

            # Start wake word listener in parallel thread if configured
            wake_word_thread = None
            if CONFIG.get("wake_word_settings", {}).get("wake_words"):
                print("🎤 Starting parallel wake word listener for 'Jarvis'...")
                def run_wake_word_listener():
                    try:
                        from .wake_word_service import WakeWordRealtimeSTTWrapper
                        from ..utils.notification import StreamingOverlayManager

                        # Create notification manager for visual feedback
                        ui_manager = StreamingOverlayManager(None)  # No rumps app for wake word thread

                        # Get wake word settings
                        wake_settings = CONFIG["wake_word_settings"]

                        # Create wake word wrapper
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
                            min_gap_between_recordings=wake_settings["min_gap_between_recordings"]
                        )

                        # Connect UI to wrapper
                        wrapper.ui_manager = ui_manager

                        # Start continuous listening with GUI support
                        wrapper.continuous_listen()
                    except Exception as e:
                        print(f"Wake word listener error: {e}")

                wake_word_thread = threading.Thread(target=run_wake_word_listener, daemon=True)
                wake_word_thread.start()
                print("✅ Wake word listener started in background with GUI support")

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
