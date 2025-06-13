import argparse
import time
import threading
from threading import Lock, Event
import pyaudio
import numpy as np
import rumps
import signal
import sys
import os
import fcntl
from pynput import keyboard
# Conditional import - only import whisper when needed
# from whisper import load_model  # Moved to conditional block below
import platform
from transcription_service import TranscriptionService, WhisperTranscriptionService, AWSTranscriptionService

HEARTBEAT_FILE = "/tmp/whisper_dictation.heartbeat"
HEARTBEAT_INTERVAL = 5 # seconds

class SingleInstanceLock:
    """Ensures only one instance of whisper_dictation runs at a time"""
    
    def __init__(self, lock_file_path=None):
        self.lock_file_path = lock_file_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            '.whisper_dictation.lock'
        )
        self.lock_file = None
        
    def acquire(self):
        """Try to acquire the lock atomically. Return True if successful, False otherwise."""
        try:
            # Use O_CREAT | O_EXCL for atomic file creation
            # This prevents TOCTOU race conditions
            import stat
            
            # Open file with exclusive creation flags
            fd = os.open(
                self.lock_file_path, 
                os.O_CREAT | os.O_WRONLY | os.O_TRUNC,
                stat.S_IRUSR | stat.S_IWUSR
            )
            
            try:
                # Apply the lock immediately after opening
                fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                # Convert to file object for easier handling
                self.lock_file = os.fdopen(fd, 'w')
                
                # Write PID to the lock file
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                
                return True
                
            except IOError:
                # Failed to acquire lock, close the file descriptor
                os.close(fd)
                # Try to remove the file we created
                try:
                    os.unlink(self.lock_file_path)
                except:
                    pass
                return False
                
        except (IOError, OSError) as e:
            # File already exists or permission denied
            return False
            
    def release(self):
        """Release the lock safely"""
        if self.lock_file:
            try:
                # Release the file lock first
                fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
            except (OSError, IOError):
                pass  # Lock may already be released
            
            try:
                # Close the file
                self.lock_file.close()
            except (OSError, IOError):
                pass
            
            self.lock_file = None
            
            # Remove the lock file
            try:
                os.unlink(self.lock_file_path)
            except (OSError, IOError):
                pass  # File may not exist or permission issues

class Recorder:
    def __init__(self, transcription_service):
        self.recording = False
        self.transcription_service = transcription_service
        self.stream = None
        self.p = None
        self.lock = Lock()
        self.frames_per_buffer = 1024
        self.recording_thread = None
        self._initialize_audio_system()

    def _initialize_audio_system(self):
        """Initialize PyAudio and create pre-warmed audio stream (PRIVACY-SAFE: not recording yet)"""
        try:
            print("Initializing pre-warmed audio system...")
            # Initialize PyAudio once at startup
            self.p = pyaudio.PyAudio()
            
            # Create audio stream but keep it STOPPED (not recording)
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                frames_per_buffer=self.frames_per_buffer,
                input=True,
                start=False  # CRITICAL: Don't start recording yet!
            )
            print("✅ Pre-warmed audio system ready (not recording)")
        except Exception as e:
            print(f"Error initializing pre-warmed audio system: {e}")
            # Fallback to old behavior if pre-warming fails
            self.stream = None
            self.p = None

    def start(self, language=None):
        with self.lock:
            if not self.recording and (self.recording_thread is None or not self.recording_thread.is_alive()):
                self.recording = True
                self.recording_thread = threading.Thread(target=self._record_impl, args=(language,))
                self.recording_thread.start()

    def stop(self):
        with self.lock:
            self.recording = False

    def cleanup(self):
        """Clean up resources when app is shutting down (not after each recording)"""
        with self.lock:
            # Stop recording if still active
            self.recording = False
            
            # Cleanup PyAudio stream (only on app shutdown)
            if self.stream is not None:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                    print("🧹 Pre-warmed audio stream closed")
                except Exception as e:
                    print(f"Error closing stream: {e}")
                finally:
                    self.stream = None
                    
            # Cleanup PyAudio instance (only on app shutdown)
            if self.p is not None:
                try:
                    self.p.terminate()
                    print("🧹 PyAudio instance terminated")
                except Exception as e:
                    print(f"Error terminating PyAudio: {e}")
                finally:
                    self.p = None
            
            # Cleanup transcription service
            if self.transcription_service:
                try:
                    self.transcription_service.cleanup()
                except Exception as e:
                    print(f"Error cleaning up transcription service: {e}")

    def _record_impl(self, language):
        frames = []
        
        try:
            # Use pre-warmed audio system for INSTANT recording start
            if self.stream is not None:
                print("🚀 Starting recording with pre-warmed audio system...")
                # INSTANT START: Just activate the existing stream
                self.stream.start_stream()
                
                # Record audio data while recording flag is set
                while self.recording:
                    try:
                        data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                        frames.append(data)
                    except IOError as e:
                        print(f"Warning: IO error during recording: {e}")
                    except Exception as e:
                        print(f"Error during recording: {e}")
                        break
                
                # Stop the stream but keep it alive for next recording
                self.stream.stop_stream()
                print("⏹️ Recording stopped (stream kept alive for next use)")
                
            else:
                # Fallback to old behavior if pre-warming failed
                print("⚠️ Falling back to old initialization method...")
                self.p = pyaudio.PyAudio()
                self.stream = self.p.open(format=pyaudio.paInt16,
                                channels=1,
                                rate=16000,
                                frames_per_buffer=self.frames_per_buffer,
                                input=True)
                
                while self.recording:
                    try:
                        data = self.stream.read(self.frames_per_buffer, exception_on_overflow=False)
                        frames.append(data)
                    except IOError as e:
                        print(f"Warning: IO error during recording: {e}")
                    except Exception as e:
                        print(f"Error during recording: {e}")
                        break
            
            # Process recorded audio if we have any frames
            if frames:
                try:
                    audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
                    audio_data_fp32 = audio_data.astype(np.float32) / 32768.0
                    self.transcription_service.transcribe(audio_data_fp32, language)
                except Exception as e:
                    print(f"Error processing audio data: {e}")
        except Exception as e:
            print(f"Error in recording implementation: {e}")
        finally:
            # DON'T call cleanup() - keep pre-warmed system alive
            pass

class GlobalKeyListener:
    def __init__(self, app, key_combination):
        self.app = app
        self.key1, self.key2 = self.parse_key_combination(key_combination)
        self.key1_pressed = False
        self.key2_pressed = False

    def parse_key_combination(self, key_combination):
        key1_name, key2_name = key_combination.split('+')
        key1 = getattr(keyboard.Key, key1_name, keyboard.KeyCode(char=key1_name))
        key2 = getattr(keyboard.Key, key2_name, keyboard.KeyCode(char=key2_name))
        return key1, key2

    def on_key_press(self, key):
        if key == self.key1:
            self.key1_pressed = True
        elif key == self.key2:
            self.key2_pressed = True

        if self.key1_pressed and self.key2_pressed:
            self.app.toggle()

    def on_key_release(self, key):
        if key == self.key1:
            self.key1_pressed = False
        elif key == self.key2:
            self.key2_pressed = False

class DoubleCommandKeyListener:
    def __init__(self, app):
        self.app = app
        self.key = keyboard.Key.cmd_r
        self.pressed = 0
        self.last_press_time = 0

    def on_key_press(self, key):
        is_listening = self.app.started
        if key == self.key:
            current_time = time.time()
            time_diff = current_time - self.last_press_time
            
            # Check for double-click: time difference < 0.5 seconds AND we have a previous press
            if not is_listening and time_diff < 0.5 and self.last_press_time > 0:  # Double click to start listening
                self.app.toggle()
            elif is_listening:  # Single click to stop listening
                self.app.toggle()
            self.last_press_time = current_time

    def on_key_release(self, key):
        pass

class StatusBarApp(rumps.App):
    def __init__(self, recorder, languages=None, max_time=None):
        super().__init__("whisper", "⏯")
        self.languages = languages
        self.current_language = languages[0] if languages is not None else None

        menu = [
            'Start Recording',
            'Stop Recording',
            None,
        ]

        if languages is not None:
            for lang in languages:
                callback = self.change_language if lang != self.current_language else None
                menu.append(rumps.MenuItem(lang, callback=callback))
            menu.append(None)
            
        self.menu = menu
        self.menu['Stop Recording'].set_callback(None)

        self.started = False
        self.recorder = recorder
        self.max_time = max_time
        self.timer = None
        self.update_timer = None  # Track update timer separately
        self.elapsed_time = 0
        self.app_lock = Lock()  # Add thread synchronization lock

    def change_language(self, sender):
        self.current_language = sender.title
        for lang in self.languages:
            self.menu[lang].set_callback(self.change_language if lang != self.current_language else None)

    @rumps.clicked('Start Recording')
    def start_app(self, _):
        print('Listening...')
        self.started = True
        self.menu['Start Recording'].set_callback(None)
        self.menu['Stop Recording'].set_callback(self.stop_app)
        self.recorder.start(self.current_language)

        # Only set timer if max_time is specified (not None)
        if self.max_time is not None and self.max_time > 0:
            self.timer = threading.Timer(self.max_time, lambda: self.stop_app(None))
            self.timer.start()
            print(f"⏱️ Recording will auto-stop after {self.max_time} seconds")
        else:
            print("⏱️ Recording with no time limit - press hotkey again to stop")

        self.start_time = time.time()
        self.update_title()

    @rumps.clicked('Stop Recording')
    def stop_app(self, _):
        if not self.started:
            return
        
        if self.timer is not None:
            self.timer.cancel()

        print('Transcribing...')
        self.title = "⏯"
        self.started = False
        self.menu['Stop Recording'].set_callback(None)
        self.menu['Start Recording'].set_callback(self.start_app)
        self.recorder.stop()
        print('Done.\n')

    def update_title(self):
        if self.started:
            self.elapsed_time = int(time.time() - self.start_time)
            minutes, seconds = divmod(self.elapsed_time, 60)
            self.title = f"({minutes:02d}:{seconds:02d}) 🔴"
            threading.Timer(1, self.update_title).start()

    def toggle(self):
        if self.started:
            self.stop_app(None)
        else:
            self.start_app(None)

# --- Heartbeat Function ---
def _update_heartbeat(stop_event: Event):
    """Periodically updates the heartbeat file with the current timestamp."""
    print("Heartbeat thread started.")
    while not stop_event.is_set():
        try:
            with open(HEARTBEAT_FILE, "w") as f:
                f.write(str(time.time()))
        except IOError as e:
            print(f"Heartbeat Error: Could not write to {HEARTBEAT_FILE}: {e}")
        except Exception as e:
            print(f"Heartbeat Error: Unexpected error: {e}")
            
        # Wait for the specified interval or until the stop event is set
        stop_event.wait(HEARTBEAT_INTERVAL)
    print("Heartbeat thread stopped.")
    # Clean up the heartbeat file when stopped
    try:
        if os.path.exists(HEARTBEAT_FILE):
            os.remove(HEARTBEAT_FILE)
            print(f"Removed heartbeat file: {HEARTBEAT_FILE}")
    except OSError as e:
        print(f"Heartbeat Cleanup Error: Could not remove {HEARTBEAT_FILE}: {e}")

def parse_args():
    parser = argparse.ArgumentParser(
        description='Dictation app using OpenAI Whisper ASR model or AWS Transcribe. By default the keyboard shortcut cmd+option '
        'starts and stops dictation')
    parser.add_argument('-m', '--model_name', type=str,
                        choices=['tiny', 'tiny.en', 'base', 'base.en', 'small', 'small.en', 'medium', 'medium.en', 'large'],
                        default='base',
                        help='Specify the whisper ASR model to use (ignored if --use_aws_transcribe is set). Options: tiny, base, small, medium, or large. '
                        'To see the  most up to date list of models along with model size, memory footprint, and estimated '
                        'transcription speed check out this [link](https://github.com/openai/whisper#available-models-and-languages). '
                        'Note that the models ending in .en are trained only on English speech and will perform better on English '
                        'language. Note that the small, medium, and large models may be slow to transcribe and are only recommended '
                        'if you find the base model to be insufficient. Default: base.')
    parser.add_argument('--use_aws_transcribe', action='store_true',
                        help='Use AWS Transcribe instead of local Whisper model. Requires AWS credentials to be configured. '
                        'When enabled, no local model will be loaded, providing faster startup and cloud-based transcription.')
    parser.add_argument('--aws_region', type=str, default='us-east-1',
                        help='AWS region to use for Transcribe service (only used with --use_aws_transcribe). Default: us-east-1.')
    parser.add_argument('-k', '--key_combination', type=str, default='cmd_l+alt' if platform.system() == 'Darwin' else 'ctrl+alt',
                        help='Specify the key combination to toggle the app. Example: cmd_l+alt for macOS '
                        'ctrl+alt for other platforms. Default: cmd_r+alt (macOS) or ctrl+alt (others).')
    parser.add_argument('--k_double_cmd', action='store_true',
                            help='If set, use double Right Command key press on macOS to toggle the app (double click to begin recording, single click to stop recording). '
                                 'Ignores the --key_combination argument.')
    parser.add_argument('-l', '--language', type=str, default=None,
                        help='Specify the two-letter language code (e.g., "en" for English) to improve recognition accuracy. '
                        'This can be especially helpful for smaller model sizes.  To see the full list of supported languages, '
                        'check out the official list [here](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py).')
    parser.add_argument('-t', '--max_time', type=float, default=None,
                        help='Specify the maximum recording time in seconds. The app will automatically stop recording after this duration. '
                        'Default: No limit (unlimited recording).')

    args = parser.parse_args()

    if args.language is not None:
        args.language = args.language.split(',')

    if not args.use_aws_transcribe and args.model_name.endswith('.en') and args.language is not None and any(lang != 'en' for lang in args.language):
        raise ValueError('If using a model ending in .en, you cannot specify a language other than English.')

    return args

def signal_handler(sig, frame):
    """Handle termination signals to clean up resources gracefully."""
    print(f"\nReceived signal {sig}, shutting down gracefully...")
    
    # Stop recording if active
    if app and app.started:
        try:
            app.stop_app(None)
        except Exception as e:
            print(f"Error stopping app: {e}")

    # Stop keyboard listener
    if listener and listener.is_alive():
        try:
            listener.stop()
            print("Keyboard listener stopped.")
        except Exception as e:
            print(f"Error stopping listener: {e}")

    # Stop heartbeat thread
    if 'heartbeat_stop_event' in globals() and heartbeat_stop_event:
        heartbeat_stop_event.set()
    if 'heartbeat_thread' in globals() and heartbeat_thread and heartbeat_thread.is_alive():
        # No join here, allow cleanup within the thread itself or finally block
        pass

    # Clean up recorder resources AFTER stopping app and listener
    if recorder:
        try:
            recorder.cleanup()
            print("Recorder resources cleaned up.")
        except Exception as e:
            print(f"Error cleaning up recorder: {e}")

    # Release single instance lock
    if 'lock' in globals() and lock:
        try:
            lock.release()
            print("Single instance lock released.")
        except Exception as e:
            print(f"Error releasing lock: {e}")

    print("Signal handler cleanup attempted. Exiting.")
    sys.exit(0)

if __name__ == "__main__":
    args = parse_args()

    # Create a single instance lock
    lock = SingleInstanceLock()
    if not lock.acquire():
        print("Another instance of whisper_dictation is already running. Exiting.")
        sys.exit(1)

    # Initialize transcription service based on user choice
    transcription_service = None
    try:
        if args.use_aws_transcribe:
            print("Initializing AWS Transcribe service...")
            transcription_service = AWSTranscriptionService(region_name=args.aws_region)
            print(f"AWS Transcribe service initialized (region: {args.aws_region})")
        else:
            print("Loading Whisper model...")
            # Import whisper only when needed for local processing
            from whisper import load_model
            model_name = args.model_name
            model = load_model(model_name)
            print(f"{model_name} model loaded")
            transcription_service = WhisperTranscriptionService(model)
    except Exception as e:
        print(f"Error initializing transcription service: {e}")
        if args.use_aws_transcribe:
            print("Make sure AWS credentials are configured and you have access to AWS Transcribe.")
            print("You can configure credentials using 'aws configure' or environment variables.")
        sys.exit(1)
    
    recorder = Recorder(transcription_service)
    
    app = StatusBarApp(recorder, args.language, args.max_time)
    if args.k_double_cmd:
        key_listener = DoubleCommandKeyListener(app)
        listener = keyboard.Listener(on_press=key_listener.on_key_press, on_release=key_listener.on_key_release)
    else:
        print(f"Using Global Key Combination listener: {args.key_combination}")
        try:
            key_listener = GlobalKeyListener(app, args.key_combination)
            listener = keyboard.Listener(on_press=key_listener.on_key_press, on_release=key_listener.on_key_release)
        except Exception as e:
            print(f"Error initializing GlobalKeyListener with combination '{args.key_combination}': {e}")
            print("Please check the --key_combination format (e.g., 'cmd+option').")
            sys.exit(1)

    # Start the selected listener
    print("Starting keyboard listener...")
    listener.start()
    print("Listener started.")

    # --- Start Heartbeat Thread ---
    heartbeat_stop_event = Event()
    heartbeat_thread = threading.Thread(target=_update_heartbeat, args=(heartbeat_stop_event,), daemon=True)
    heartbeat_thread.start()

    # Register signal handlers for graceful shutdown
    # Ensure we handle both interrupt (Ctrl+C) and termination signals
    def signal_handler_wrapper(sig, frame):
        signal_handler(sig, frame)
    
    signal.signal(signal.SIGINT, signal_handler_wrapper)
    signal.signal(signal.SIGTERM, signal_handler_wrapper)

    service_type = "AWS Transcribe" if args.use_aws_transcribe else f"Whisper ({args.model_name})"
    print(f"Running with {service_type}... (Press Ctrl+C to exit)")
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit) as e:
        print(f"Main loop interrupted ({type(e).__name__}). Shutting down...")
    finally:
        # --- Final Cleanup ---
        print("Entering finally block for cleanup...")
        
        # Ensure listener is stopped
        if listener and listener.is_alive():
            try:
                listener.stop()
                print("Listener stopped in finally block.")
            except Exception as e:
                 print(f"Error stopping listener in finally: {e}")

        # Ensure heartbeat thread is stopped and file removed
        if heartbeat_stop_event and not heartbeat_stop_event.is_set():
            heartbeat_stop_event.set()
        if heartbeat_thread and heartbeat_thread.is_alive():
            heartbeat_thread.join(timeout=HEARTBEAT_INTERVAL + 1) # Wait slightly longer than interval
            if heartbeat_thread.is_alive():
                 print("Warning: Heartbeat thread did not exit cleanly.")
        # Attempt cleanup again in case thread missed it
        try:
            if os.path.exists(HEARTBEAT_FILE):
                os.remove(HEARTBEAT_FILE)
                print(f"Heartbeat file removed in finally block.")
        except OSError as e:
             print(f"Error removing heartbeat file in finally: {e}")

        # Ensure recorder is cleaned up (might be redundant if signal handler ran)
        if recorder:
            try:
                recorder.cleanup()
                print("Recorder cleaned up in finally block.")
            except Exception as e:
                 print(f"Error cleaning up recorder in finally: {e}")

        # Release the lock when exiting
        if lock:
            try:
                lock.release()
                print("Single instance lock released in finally block.")
            except Exception as e:
                print(f"Error releasing lock in finally: {e}")

        print("Cleanup in finally block complete.")

