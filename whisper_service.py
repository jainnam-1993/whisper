#!/usr/bin/env python3

import os
import signal
import subprocess
import sys
import time
import fcntl
import psutil
from typing import Optional

HEARTBEAT_FILE = "/tmp/whisper_dictation.heartbeat" # Path to the heartbeat file
HEARTBEAT_TIMEOUT = 15 # Max seconds since last heartbeat before considering stale

class SingleInstanceException(Exception):
    pass

class WhisperService:
    def __init__(self, no_restart=False):
        self.process = None
        self.should_run = True
        self.no_restart = no_restart  # Testing mode - disable automatic restarts
        self.lock_file = None
        self.whisper_dir = os.path.dirname(os.path.abspath(__file__))
        self.venv_dir = os.path.join(self.whisper_dir, "venv")
        self.crash_times = []
        self.max_crashes = 3
        self.cooldown_period = 300  # 5 minutes
        self.initial_backoff = 5  # 5 seconds
        self.setup_signal_handlers()
        self.ensure_single_instance()
        if self.no_restart:
            print("Starting Whisper Service in TESTING MODE (no automatic restarts)...")
        else:
            print("Starting Whisper Service...")

    def ensure_single_instance(self):
        """Ensure only one instance of the service is running"""
        lock_path = "/tmp/whisper_service.lock"
        
        # Kill any existing whisper processes before claiming lock
        self.kill_all_whisper_processes()
        
        # Clean up stale lock file if it exists
        if os.path.exists(lock_path):
            try:
                with open(lock_path, 'r') as f:
                    try:
                        old_pid = int(f.read().strip())
                        if not psutil.pid_exists(old_pid):
                            os.unlink(lock_path)
                        else:
                            # Active process exists, kill it
                            try:
                                psutil.Process(old_pid).kill()
                                time.sleep(1)
                                os.unlink(lock_path)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
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
            
    def kill_all_whisper_processes(self):
        """Kill all existing whisper processes"""
        killed_pids = []
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                if proc.info['cmdline']:
                    cmdline_str = ' '.join(proc.info['cmdline'])
                    if ('whisper_dictation.py' in cmdline_str or 
                        'whisper_service.py' in cmdline_str) and proc.info['pid'] != os.getpid():
                        print(f"Killing existing whisper process PID: {proc.info['pid']}")
                        psutil.Process(proc.info['pid']).kill()
                        killed_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Wait for all killed processes to actually terminate
        if killed_pids:
            print(f"Killed {len(killed_pids)} existing whisper processes")
            max_wait = 10  # Maximum wait time in seconds
            start_time = time.time()
            
            while killed_pids and (time.time() - start_time) < max_wait:
                still_running = []
                for pid in killed_pids:
                    try:
                        if psutil.pid_exists(pid):
                            still_running.append(pid)
                    except:
                        pass
                killed_pids = still_running
                if killed_pids:
                    time.sleep(0.5)
            
            if killed_pids:
                print(f"Warning: {len(killed_pids)} processes still running after cleanup")
            else:
                print("All processes successfully terminated")
        
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
        """Verify if the whisper process is healthy by checking PID and heartbeat file."""
        if not self.process:
            return False
            
        try:
            # 1. Basic Process Check (PID exists, not zombie)
            proc = psutil.Process(self.process.pid)
            if not proc.is_running() or proc.status() == 'zombie':
                print(f"Health Check Fail: Process PID {self.process.pid} not running or zombie.")
                return False
                
            # 2. Heartbeat File Check
            if not os.path.exists(HEARTBEAT_FILE):
                # Allow some grace time initially for the file to be created
                if time.time() - proc.create_time() > HEARTBEAT_TIMEOUT * 2:
                     print(f"Health Check Fail: Heartbeat file {HEARTBEAT_FILE} missing after grace period.")
                     return False
                else:
                     # Still within grace period, assume ok for now
                     return True 

            last_heartbeat_time = 0
            try:
                with open(HEARTBEAT_FILE, 'r') as f:
                    last_heartbeat_time = float(f.read().strip())
            except (IOError, ValueError) as e:
                print(f"Health Check Warning: Could not read heartbeat file {HEARTBEAT_FILE}: {e}")
                # If we can't read it, assume stale after grace period
                if time.time() - proc.create_time() > HEARTBEAT_TIMEOUT * 2:
                     return False
                else:
                     return True

            time_since_heartbeat = time.time() - last_heartbeat_time
            if time_since_heartbeat > HEARTBEAT_TIMEOUT:
                print(f"Health Check Fail: Last heartbeat {time_since_heartbeat:.1f}s ago (threshold {HEARTBEAT_TIMEOUT}s).")
                return False
                
            # If all checks pass
            return True
            
        except psutil.NoSuchProcess:
            print(f"Health Check Fail: Process PID {self.process.pid} does not exist.")
            return False
        except psutil.AccessDenied:
             print(f"Health Check Warning: Access denied checking PID {self.process.pid}.")
             # Can't verify, assume ok for now to avoid unnecessary restarts
             return True
        except Exception as e:
             print(f"Health Check Error: Unexpected error verifying PID {self.process.pid}: {e}")
             # Assume ok on unexpected error
             return True

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
        
        # Use local Whisper model with double-cmd key listener
        command_args = [
            python_executable,
            whisper_script,
            "-m", "medium",  # Use base model for good balance of speed/accuracy
            "-l", "en",
            "--k_double_cmd",  # Using local Whisper model
        ]
        
        try:
            # Launch directly, without shell, with proper process group management
            self.process = subprocess.Popen(
                command_args,
                cwd=self.whisper_dir,
                start_new_session=True,  # Create new process group for proper cleanup
                # No shell=True
                # No stdout=subprocess.PIPE
                # No stderr=subprocess.STDOUT
                # No executable='/bin/zsh' needed when shell=False
            )
            print(f"Started Whisper process with PID: {self.process.pid}")
            
            # Give the process some time to load initially
            print("Waiting for model to load...")
            time.sleep(10) # Reduced delay for faster startup
            
            if self.process.poll() is not None:
                print(f"Process exited early with code: {self.process.poll()}")
                return False
                
            print("Service ready")
            return True
        except Exception as e:
            print(f"Error starting process: {e}")
            return False

    def stop_process(self) -> None:
        """Stop the Whisper process if it's running"""
        if self.process:
            print(f"Stopping Whisper process (PID: {self.process.pid})...")
            try:
                # First, kill all child processes
                try:
                    proc = psutil.Process(self.process.pid)
                    children = proc.children(recursive=True)
                    for child in children:
                        print(f"Killing child process PID: {child.pid}")
                        child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                # Try to terminate gracefully first
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)  # Reduced timeout
                except subprocess.TimeoutExpired:
                    print("Process didn't terminate gracefully, forcing...")
                    self.process.kill()
                    self.process.wait(timeout=2)  # Ensure it's dead
                    
            except Exception as e:
                print(f"Error stopping process: {e}")
            finally:
                self.process = None
                
        # Kill any remaining whisper processes (nuclear option)
        orphaned_pids = []
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if proc.info['cmdline'] and any('whisper_dictation.py' in str(arg) for arg in proc.info['cmdline']):
                        print(f"Killing orphaned whisper process PID: {proc.info['pid']}")
                        psutil.Process(proc.info['pid']).kill()
                        orphaned_pids.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"Error in cleanup: {e}")
        
        # Wait for orphaned processes to terminate
        if orphaned_pids:
            max_wait = 5
            start_time = time.time()
            while orphaned_pids and (time.time() - start_time) < max_wait:
                still_running = []
                for pid in orphaned_pids:
                    try:
                        if psutil.pid_exists(pid):
                            still_running.append(pid)
                    except:
                        pass
                orphaned_pids = still_running
                if orphaned_pids:
                    time.sleep(0.5)

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
                if self.no_restart:
                    print("Process stopped. Testing mode enabled - NOT restarting automatically.")
                    print("Service will exit. Use 'python manage_whisper.py start' to restart manually.")
                    break
                elif self.should_restart():
                    print("Starting/Restarting Whisper process...")
                    if not self.start_process():
                        print("Failed to start process, retrying...")
                        time.sleep(5)
                        continue
            time.sleep(10)  # Health check interval

        print("Whisper Service stopped.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Whisper Service Wrapper')
    parser.add_argument('--no-restart', action='store_true',
                        help='Testing mode: disable automatic restarts when process fails')
    args = parser.parse_args()
    
    try:
        service = WhisperService(no_restart=args.no_restart)
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