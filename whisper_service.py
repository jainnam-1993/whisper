#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import time
import fcntl
import psutil
from typing import Optional

class SingleInstanceException(Exception):
    pass

class WhisperService:
    def __init__(self):
        self.process = None
        self.should_run = True
        self.lock_file = None
        self.whisper_dir = os.path.dirname(os.path.abspath(__file__))
        self.venv_dir = os.path.join(self.whisper_dir, "venv")
        self.crash_times = []
        self.max_crashes = 3
        self.cooldown_period = 300  # 5 minutes
        self.initial_backoff = 5  # 5 seconds
        self.setup_signal_handlers()
        self.ensure_single_instance()
        print("Starting Whisper Service...")

    def ensure_single_instance(self):
        """Ensure only one instance of the service is running"""
        lock_path = "/tmp/whisper_service.lock"
        
        # Clean up stale lock file if it exists
        if os.path.exists(lock_path):
            try:
                with open(lock_path, 'r') as f:
                    try:
                        old_pid = int(f.read().strip())
                        if not psutil.pid_exists(old_pid):
                            os.unlink(lock_path)
                    except (ValueError, psutil.NoSuchProcess):
                        os.unlink(lock_path)
            except (IOError, OSError):
                pass

        self.lock_file = open(lock_path, "w")
        try:
            fcntl.lockf(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
        except IOError:
            self.lock_file.close()
            raise SingleInstanceException("Another instance is already running")
        
    def setup_signal_handlers(self):
        """Set up handlers for graceful shutdown"""
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\nReceived shutdown signal. Stopping Whisper service...")
        self.should_run = False
        if self.process:
            self.stop_process()
        if self.lock_file:
            try:
                fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
                os.unlink("/tmp/whisper_service.lock")
            except:
                pass
        sys.exit(0)

    def verify_process_health(self) -> bool:
        """Verify if the whisper process is healthy"""
        if not self.process:
            return False
            
        try:
            # Check if main process is alive
            if self.process.poll() is not None:
                return False
                
            # Give the process some time to load on first check
            # This prevents rapid restarts while the model is loading
            proc = psutil.Process(self.process.pid)
            if proc.is_running() and proc.status() != 'zombie':
                return True
                
            return False
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def should_restart(self) -> bool:
        now = time.time()
        # Remove crashes older than cooldown period
        self.crash_times = [t for t in self.crash_times if (now - t) < self.cooldown_period]
        
        if len(self.crash_times) >= self.max_crashes:
            oldest_crash = min(self.crash_times)
            if (now - oldest_crash) < self.cooldown_period:
                print(f"Too many crashes in {self.cooldown_period} seconds, waiting for cooldown...")
                time.sleep(self.cooldown_period)
                self.crash_times.clear()
            
        self.crash_times.append(now)
        backoff = self.initial_backoff * (2 ** (len(self.crash_times) - 1))
        backoff = min(backoff, 300)  # Cap at 5 minutes
        time.sleep(backoff)
        return True

    def start_process(self) -> bool:
        # Construct the command as a list for direct execution
        python_executable = os.path.join(self.venv_dir, "bin", "python")
        whisper_script = os.path.join(self.whisper_dir, "whisper_dictation.py")
        
        # Ensure arguments match the intended logic (using double-cmd)
        command_args = [
            python_executable,
            whisper_script,
            "-m", "large",
            "-l", "en",
            "--k_double_cmd", # Corrected: Use double dash for the flag
        ]
        
        try:
            # Launch directly, without shell, inheriting stdio
            self.process = subprocess.Popen(
                command_args,
                cwd=self.whisper_dir,
                # No shell=True
                # No stdout=subprocess.PIPE
                # No stderr=subprocess.STDOUT
                # No executable='/bin/zsh' needed when shell=False
            )
            print(f"Started Whisper process with PID: {self.process.pid}")
            
            # Give the process some time to load initially
            # Note: We can't easily see the "model loaded" message anymore,
            # but we can still check if the process exits early.
            print("Waiting for model to load (may take a minute or two)...")
            time.sleep(30) # Keep a reasonable delay
            
            if self.process.poll() is not None:
                print(f"Process exited early with code: {self.process.poll()}")
                # Log the exit code or potential errors if possible (though stdout/err aren't captured)
                return False
                
            print("Model should be loaded now, service ready")
            return True
        except Exception as e:
            print(f"Error starting process: {e}")
            return False

    def stop_process(self) -> None:
        """Stop the Whisper process if it's running"""
        if self.process:
            print(f"Stopping Whisper process (PID: {self.process.pid})...")
            try:
                # Try to terminate gracefully first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate gracefully, forcing...")
                    self.process.kill()
                    
                # Clean up any child processes
                try:
                    proc = psutil.Process(self.process.pid)
                    children = proc.children(recursive=True)
                    for child in children:
                        child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            except Exception as e:
                print(f"Error stopping process: {e}")
            finally:
                self.process = None

    def check_process(self) -> bool:
        """Check if the process is still running and healthy"""
        if not self.process:
            return False
        
        return_code = self.process.poll()
        if return_code is not None:
            if return_code < 0:  # Negative return code indicates crash
                print(f"Process crashed with signal {-return_code}")
            else:
                print(f"Process exited with code: {return_code}")
            return False
            
        # Verify process health
        if not self.verify_process_health():
            print("Process is running but not healthy")
            return False
            
        return True

    def run(self) -> None:
        """Main service loop with health checks every 10 seconds"""
        while self.should_run:
            if not self.check_process():
                if self.should_restart():
                    print("Starting/Restarting Whisper process...")
                    if not self.start_process():
                        print("Failed to start process, retrying...")
                        time.sleep(5)
                        continue
            time.sleep(10)  # Health check interval

        print("Whisper Service stopped.")

def main():
    try:
        service = WhisperService()
        service.run()
    except SingleInstanceException as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt. Shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 