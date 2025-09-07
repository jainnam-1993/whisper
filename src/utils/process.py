#!/usr/bin/env python3
"""
Process Utilities for Whisper Dictation
Provides utilities for process management, locking, and thread safety
"""

import os
import sys
import fcntl
import threading
from typing import Optional


class SingleInstanceLock:
    """
    Ensures only one instance of the application runs at a time using file-based locking
    
    Features:
    - File-based locking with PID tracking
    - Automatic cleanup on exit
    - Thread-safe operations
    """
    
    def __init__(self, lock_file_path: Optional[str] = None):
        """
        Initialize single instance lock
        
        Args:
            lock_file_path: Custom path for lock file, or None for default
        """
        self.lock_file_path = lock_file_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '.whisper_instance.lock'
        )
        self.lock_file = None
        self._lock = threading.RLock()
    
    def acquire(self) -> bool:
        """
        Try to acquire the lock
        
        Returns:
            bool: True if successful, False if another instance has the lock
        """
        with self._lock:
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
                    self.lock_file = None
                return False
    
    def release(self) -> None:
        """Release the lock"""
        with self._lock:
            if self.lock_file:
                try:
                    fcntl.lockf(self.lock_file, fcntl.LOCK_UN)
                    self.lock_file.close()
                finally:
                    self.lock_file = None
                    try:
                        os.unlink(self.lock_file_path)
                    except:
                        pass  # Ignore cleanup errors
    
    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Another instance is already running")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


def create_daemon_thread(target, name: Optional[str] = None, args=(), kwargs=None) -> threading.Thread:
    """
    Create a daemon thread with standardized configuration
    
    Args:
        target: Function to run in the thread
        name: Optional thread name
        args: Arguments for the target function
        kwargs: Keyword arguments for the target function
        
    Returns:
        threading.Thread: Configured daemon thread (not started)
    """
    kwargs = kwargs or {}
    thread = threading.Thread(
        target=target,
        name=name,
        args=args,
        kwargs=kwargs,
        daemon=True
    )
    return thread


# Legacy compatibility
def create_single_instance_lock(lock_file_path: Optional[str] = None) -> SingleInstanceLock:
    """Factory function for creating single instance locks"""
    return SingleInstanceLock(lock_file_path)