#!/usr/bin/env python3
import time
import os
import subprocess
import threading
import traceback
import sys
import fcntl
from pynput import keyboard
from accessibility_utils import _execute_applescript_safely

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

class DockerCommunicator:
    def __init__(self, container_name="whisper-dictation"):
        self.container_name = container_name
        self.is_transcribing = False
        self.recording_thread = None
        self.audio_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio.wav")
        self.min_recording_time = 3.0  # Increased minimum recording time in seconds
        self.clipboard = ClipboardManager()

    def start_recording(self):
        """Start recording audio from the host system"""
        if self.is_transcribing:
            return
            
        self.is_transcribing = True
        self.start_time = time.time()
        print("Started recording...")
        
        # Start recording using system audio tools
        # Using sox to record audio with noise reduction
        try:
            self.recording_process = subprocess.Popen(
                ["rec", "-r", "16000", "-c", "1", self.audio_file],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.is_transcribing = False
        
    def stop_recording(self):
        """Stop recording and send to Docker container for transcription"""
        if not self.is_transcribing:
            return
            
        try:
            # Ensure we record for at least the minimum time
            current_time = time.time()
            elapsed = current_time - self.start_time
            if elapsed < self.min_recording_time:
                wait_time = self.min_recording_time - elapsed
                print(f"Recording for {wait_time:.1f} more seconds to reach minimum...")
                time.sleep(wait_time)
                
            print("Stopping recording and transcribing...")
            
            # Terminate recording process
            if hasattr(self, 'recording_process'):
                self.recording_process.terminate()
                self.recording_process.wait()
            
            # Check if the audio file exists and has content
            if os.path.exists(self.audio_file) and os.path.getsize(self.audio_file) > 1000:  # Require at least 1KB
                print(f"Audio file size: {os.path.getsize(self.audio_file)} bytes")
                
                # Copy the audio file to the container
                copy_result = subprocess.run([
                    "docker", "cp", 
                    self.audio_file, 
                    f"{self.container_name}:/app/audio_to_transcribe.wav"
                ], capture_output=True, text=True)
                
                if copy_result.returncode != 0:
                    print(f"Error copying file to container: {copy_result.stderr}")
                    self.is_transcribing = False
                    return
                
                # Execute transcription in the container using the transcribe.py script
                result = subprocess.run([
                    "docker", "exec", 
                    self.container_name, 
                    "python", "/app/transcribe.py", "/app/audio_to_transcribe.wav"
                ], capture_output=True, text=True)
                
                print(f"Transcription process output: {result.stdout}")
                if result.stderr:
                    print(f"Transcription errors: {result.stderr}")
                
                # Get the transcription result
                result = subprocess.run([
                    "docker", "exec", 
                    self.container_name, 
                    "cat", "/app/last_transcription.txt"
                ], capture_output=True, text=True)
                
                # Copy and paste the result
                if result.stdout and result.stdout.strip():
                    transcription = result.stdout.strip()
                    print(f"Transcription: {transcription}")
                    
                    # Preserve original clipboard content
                    self.clipboard.preserve_clipboard()
                    
                    # Copy to clipboard
                    if self.clipboard.copy_to_clipboard(transcription):
                        print("Text copied to clipboard")
                        # Small delay before pasting
                        time.sleep(0.5)
                        
                        # Try a direct system paste using AppleScript
                        print("Attempting direct system paste...")
                        # Add a longer wait to ensure focus is back to editor
                        time.sleep(1)
                        
                        # Paste the text using AppleScript
                        if self.clipboard.paste_from_clipboard():
                            print("Text pasted from clipboard")
                            # Restore original clipboard content after successful paste
                            time.sleep(0.5)  # Brief delay to ensure paste is complete
                            self.clipboard.restore_clipboard()
                        else:
                            print("Failed to paste text - text is in clipboard, please paste manually (Cmd+V)")
                            print("Original clipboard will be restored after you paste manually")
                            # Note: In manual paste case, we don't restore immediately to allow user to paste
                            
                            # As a fallback, display what's in the clipboard
                            try:
                                clip_content = subprocess.run(["pbpaste"], capture_output=True, text=True)
                                print(f"Current clipboard content: '{clip_content.stdout.strip()}'")
                            except:
                                print("Could not get clipboard content")
                    else:
                        print("Failed to copy text to clipboard")
                else:
                    print("No transcription result received or empty result")
                
                # Clean up the audio file
                os.remove(self.audio_file)
            else:
                print("Audio file is too small or doesn't exist")
        except Exception as e:
            print(f"Error in stop_recording: {e}")
            traceback.print_exc()
        finally:
            self.is_transcribing = False

class DoubleCommandKeyListener:
    def __init__(self, docker_communicator):
        self.communicator = docker_communicator
        self.key = keyboard.Key.cmd_r
        self.last_press_time = 0
        
    def on_key_press(self, key):
        try:
            if key == self.key:
                current_time = time.time()
                
                # If not recording and double-pressed (within 0.5 seconds)
                if not self.communicator.is_transcribing and current_time - self.last_press_time < 0.5:
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

def check_docker_container():
    """Check if Docker is running and container exists, start if needed"""
    try:
        # Check if Docker is running
        docker_status = subprocess.run(
            ["docker", "info"], 
            capture_output=True, 
            text=True
        )
        
        if docker_status.returncode != 0:
            print("Docker is not running. Please start Docker Desktop.")
            return False
            
        # Check if container exists
        container_check = subprocess.run(
            ["docker", "ps", "-q", "-f", "name=whisper-dictation"], 
            capture_output=True, 
            text=True
        )
        
        if not container_check.stdout:
            print("Whisper Docker container is not running. Starting it...")
            subprocess.run(["./docker-startup.sh"])
            # Wait for container to start
            for i in range(20):  # Wait up to 20 seconds
                print(f"Waiting for container to start ({i+1}/20)...")
                time.sleep(1)
                container_check = subprocess.run(
                    ["docker", "ps", "-q", "-f", "name=whisper-dictation"], 
                    capture_output=True, 
                    text=True
                )
                if container_check.stdout:
                    print("Container started successfully.")
                    # Give it a bit more time to load model
                    time.sleep(5)
                    return True
            
            print("Container failed to start within timeout.")
            return False
            
        return True
    except Exception as e:
        print(f"Error checking Docker: {e}")
        traceback.print_exc()
        return False

def main():
    try:
        # Create a single instance lock
        lock = SingleInstanceLock()
        if not lock.acquire():
            print("Another instance is already running. Exiting.")
            sys.exit(1)
        
        try:
            # Check Docker container
            if not check_docker_container():
                print("Aborting due to Docker container issues.")
                return
                
            print("Starting key listener for double Command press...")
            print("Double-press Right Command to start recording")
            print("Single-press Right Command while recording to stop and transcribe")
            
            docker_communicator = DockerCommunicator()
            key_listener = DoubleCommandKeyListener(docker_communicator)
            
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