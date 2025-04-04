#!/usr/bin/env python3

import os
import signal
import sys
import psutil
import time
import subprocess
from typing import Optional, Tuple

def verify_process_functionality(proc: psutil.Process) -> bool:
    """Verify if the process is actually functioning by checking its children"""
    try:
        # Check if the main process is responding
        if not proc.is_running():
            return False
            
        # Give a short time for children to be visible
        time.sleep(0.5)
        
        # Check for whisper_dictation.py child process
        children = proc.children(recursive=True)
        for child in children:
            try:
                if 'whisper_dictation.py' in ' '.join(child.cmdline()):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def find_whisper_process() -> Tuple[Optional[psutil.Process], bool]:
    """Find the running Whisper service process and verify its functionality"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and 'whisper_service.py' in ' '.join(proc.info['cmdline']):
                is_functional = verify_process_functionality(proc)
                return proc, is_functional
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None, False

def cleanup_stale_process():
    """Clean up any stale Whisper service processes"""
    proc, is_functional = find_whisper_process()
    if proc and not is_functional:
        try:
            print(f"Found stale Whisper service (PID: {proc.pid}). Cleaning up...")
            proc.terminate()
            proc.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
        time.sleep(2)  # Wait for cleanup

def start_service():
    """Start the Whisper service"""
    proc, is_functional = find_whisper_process()
    
    if proc:
        if is_functional:
            print("Whisper service is already running and functional")
            return
        else:
            cleanup_stale_process()
    
    try:
        # Start the service with working directory explicitly set
        service_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'whisper_service.py')
        subprocess.Popen([
            'python3',
            service_path
        ], cwd=os.path.dirname(service_path))
        
        # Wait for service to start and verify
        time.sleep(2)
        proc, is_functional = find_whisper_process()
        if proc and is_functional:
            print("Whisper service started successfully")
        else:
            print("Warning: Service started but may not be fully functional")
    except Exception as e:
        print(f"Error starting service: {e}")

def stop_service():
    """Stop the Whisper service"""
    proc, _ = find_whisper_process()
    if not proc:
        print("Whisper service is not running")
        return

    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        print("Whisper service stopped")
    except Exception as e:
        print(f"Error stopping service: {e}")

def check_status():
    """Check if the Whisper service is running and functional"""
    proc, is_functional = find_whisper_process()
    if proc:
        status = "running and functional" if is_functional else "running but not responding"
        print(f"Whisper service is {status} (PID: {proc.pid})")
    else:
        print("Whisper service is not running")

def print_usage():
    """Print usage instructions"""
    print("Usage: manage_whisper.py [command]")
    print("Commands:")
    print("  start   - Start the Whisper service")
    print("  stop    - Stop the Whisper service")
    print("  status  - Check service status")
    print("  restart - Restart the service")

def main():
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    
    if command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "status":
        check_status()
    elif command == "restart":
        stop_service()
        time.sleep(2)  # Wait for service to stop
        start_service()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

if __name__ == "__main__":
    main() 