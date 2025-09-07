#!/usr/bin/env python3
"""
Streaming Notification Overlay - macOS-style dictation display

A lightweight, tkinter-free solution for real-time transcription display
using system notifications and a simple overlay approach.
"""

import subprocess
import threading
import time
import os
from typing import Optional, Callable


class MacOSNotificationManager:
    """
    Manager for macOS native notifications that can be updated.
    Uses osascript to create sleek, system-native notifications.
    """
    
    def __init__(self):
        self.current_notification = None
        self.is_active = False
        self.update_thread = None
        self._stop_updates = threading.Event()
        
    def show_transcription_start(self):
        """Show initial notification indicating transcription has started."""
        try:
            # Create initial notification
            script = '''
            display notification "🎤 Listening..." with title "Whisper Dictation" subtitle "Say something..."
            '''
            subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
            self.is_active = True
            return True
        except subprocess.CalledProcessError:
            return False
    
    def show_final_transcription(self, text: str):
        """Show final transcription result."""
        try:
            # Truncate text if too long for notification
            display_text = text[:100] + "..." if len(text) > 100 else text
            
            script = f'''
            display notification "{display_text}" with title "✅ Transcription Complete" subtitle "Text copied to clipboard"
            '''
            subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
            self.is_active = False
            return True
        except subprocess.CalledProcessError:
            return False
    
    def cleanup(self):
        """Cleanup any active notifications."""
        self.is_active = False
        self._stop_updates.set()


class SimpleStreamingOverlay:
    """
    A simple streaming overlay using terminal output and system notifications.
    Falls back gracefully when GUI libraries aren't available.
    """
    
    def __init__(self):
        self.notification_manager = MacOSNotificationManager()
        self.is_recording = False
        self.current_text = ""
        self.last_update_time = 0
        
    def start_recording(self):
        """Start recording indication."""
        if not self.is_recording:
            self.is_recording = True
            self.current_text = ""
            
            # Show system notification
            success = self.notification_manager.show_transcription_start()
            
            # Also print to terminal for debugging
            print("🎤 " + "="*50)
            print("🎤 Whisper Dictation - Listening...")
            print("🎤 " + "="*50)
            
            return success
    
    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription text."""
        if not self.is_recording and not is_final:
            return
            
        self.current_text = text
        current_time = time.time()
        
        # Throttle terminal updates to avoid spam
        if current_time - self.last_update_time > 0.2:  # Max 5 updates per second
            prefix = "✅" if is_final else "🔄"
            status = "FINAL" if is_final else "partial"
            
            # Clear previous line and show new text
            print(f"\r{prefix} [{status}] {text[:80]}" + " " * 20, end="", flush=True)
            self.last_update_time = current_time
        
        # If this is final, show system notification
        if is_final:
            self.stop_recording()
            if text.strip():
                self.notification_manager.show_final_transcription(text)
            print()  # New line after final text
    
    def stop_recording(self):
        """Stop recording indication."""
        if self.is_recording:
            self.is_recording = False
            print("\n🎤 Transcription complete.")
            print("=" * 50)
    
    def cleanup(self):
        """Cleanup resources."""
        self.notification_manager.cleanup()
        if self.is_recording:
            self.stop_recording()


class StreamingOverlayManager:
    """
    Drop-in replacement for the complex UIManager that works without tkinter.
    Provides the same interface but uses system notifications instead.
    """
    
    def __init__(self, rumps_app=None):
        self.overlay = SimpleStreamingOverlay()
        self.rumps_app = rumps_app  # Keep for compatibility
        self.is_recording = False
        
    def start_recording(self):
        """Start recording and show notification."""
        if not self.is_recording:
            self.is_recording = True
            self.overlay.start_recording()
            
            # Update menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = "🎤"
    
    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription text."""
        self.overlay.update_transcription(text, is_final=is_final)
        
        if is_final:
            self.is_recording = False
            # Restore menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = None  # Default icon
    
    def stop_recording(self):
        """Stop recording and hide notification."""
        if self.is_recording:
            self.is_recording = False
            self.overlay.stop_recording()
            
            # Restore menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = None  # Default icon
    
    def update_audio_levels(self, audio_data):
        """Placeholder for audio level updates (not needed for notifications)."""
        pass
    
    def cleanup(self):
        """Cleanup resources."""
        self.overlay.cleanup()


# For backward compatibility, alias the manager classes
UIManager = StreamingOverlayManager


if __name__ == "__main__":
    def test_notification_system():
        """Test the notification-based overlay system."""
        manager = StreamingOverlayManager()
        
        try:
            print("Testing streaming notification system...")
            
            # Start recording
            manager.start_recording()
            time.sleep(1)
            
            # Simulate streaming updates
            test_phrases = [
                "Hello",
                "Hello world",
                "Hello world this is",
                "Hello world this is a test",
                "Hello world this is a test of the notification system."
            ]
            
            for i, phrase in enumerate(test_phrases):
                is_final = (i == len(test_phrases) - 1)
                manager.update_transcription(phrase, is_final=is_final)
                time.sleep(0.5)
            
            print("\nTest completed!")
            
        except KeyboardInterrupt:
            print("\nTest interrupted")
        finally:
            manager.cleanup()
    
    test_notification_system()