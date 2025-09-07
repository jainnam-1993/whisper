#!/usr/bin/env python3
"""
Streaming Status Bar GUI - Native macOS status bar integration

Native macOS status bar integration for whisper transcription system.
Replaces OSA script notifications with proper status bar icons and text.
"""

import threading
import time
import os
from typing import Optional, Callable

# Import the native status bar manager
try:
    from .native_status_bar import NativeStatusBarManager
    STATUS_BAR_AVAILABLE = True
except ImportError:
    STATUS_BAR_AVAILABLE = False
    print("⚠️ Native status bar not available, using fallback")


class StatusBarGUIManager:
    """
    Manager for native macOS status bar integration.
    Provides rich visual feedback through status bar icons and text.
    """
    
    def __init__(self):
        self.native_manager = None
        self.is_active = False
        self._init_status_bar()
        
    def _init_status_bar(self):
        """Initialize the native status bar manager."""
        if STATUS_BAR_AVAILABLE:
            try:
                self.native_manager = NativeStatusBarManager()
                print("✅ Status bar GUI initialized")
            except Exception as e:
                print(f"⚠️ Status bar init failed: {e}")
                self.native_manager = None
        
    def show_transcription_start(self):
        """Show initial status bar indication that transcription has started."""
        if self.native_manager:
            success = self.native_manager.start_recording()
            self.is_active = success
            return success
        return False
    
    def show_processing(self, stage: str = "Processing"):
        """Show processing stage in status bar."""
        if self.native_manager:
            self.native_manager.show_processing(stage)
            return True
        return False
    
    def update_progress(self, value: int, stage: Optional[str] = None):
        """Update progress with optional stage name."""
        if self.native_manager:
            self.native_manager.update_progress(value, stage)
            return True
        return False
    
    def show_final_transcription(self, text: str):
        """Show final transcription result in status bar."""
        if self.native_manager:
            self.native_manager.update_transcription(text, is_final=True)
            self.is_active = False
            return True
        return False
    
    def cleanup(self):
        """Cleanup status bar resources."""
        self.is_active = False
        if self.native_manager:
            self.native_manager.cleanup()


class SimpleStreamingOverlay:
    """
    A simple streaming overlay using native macOS status bar and terminal output.
    Provides professional visual feedback without intrusive notifications.
    """
    
    def __init__(self):
        self.status_manager = StatusBarGUIManager()
        self.is_recording = False
        self.current_text = ""
        self.last_update_time = 0
        
    def start_recording(self):
        """Start recording indication."""
        if not self.is_recording:
            self.is_recording = True
            self.current_text = ""
            
            # Show status bar indication
            success = self.status_manager.show_transcription_start()
            
            # Also print to terminal for debugging
            print("🎤 " + "="*50)
            print("🎤 Whisper Dictation - Listening...")
            print("🎤 " + "="*50)
            
            return success
    
    def show_processing(self, stage: str = "Processing"):
        """Show processing stage."""
        return self.status_manager.show_processing(stage)
    
    def update_progress(self, value: int, stage: Optional[str] = None):
        """Update progress."""
        return self.status_manager.update_progress(value, stage)
    
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
            print(f"{prefix} [{status}] {text[:80]}" + " " * 20, end="", flush=True)
            self.last_update_time = current_time
        
        # If this is final, show status bar notification
        if is_final:
            self.stop_recording()
            if text.strip():
                self.status_manager.show_final_transcription(text)
            print()  # New line after final text
    
    def stop_recording(self):
        """Stop recording indication."""
        if self.is_recording:
            self.is_recording = False
            print("🎤 Transcription complete.")
            print("=" * 50)
    
    def cleanup(self):
        """Cleanup resources."""
        self.status_manager.cleanup()
        if self.is_recording:
            self.stop_recording()


class StreamingOverlayManager:
    """
    Drop-in replacement using native macOS status bar integration.
    Provides the same interface but uses status bar GUI instead of OSA notifications.
    """
    
    def __init__(self, rumps_app=None):
        self.overlay = SimpleStreamingOverlay()
        self.rumps_app = rumps_app  # Keep for compatibility
        self.is_recording = False
        
    def start_recording(self):
        """Start recording and show status bar indication."""
        if not self.is_recording:
            self.is_recording = True
            self.overlay.start_recording()
            
            # Update menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = "🎤"
    
    def show_processing(self, stage: str = "Processing"):
        """Show processing stage in status bar (NEW method from HANDOFF.md)."""
        return self.overlay.show_processing(stage)
    
    def update_progress(self, value: int, stage: Optional[str] = None):
        """Update progress with optional stage name (NEW method from HANDOFF.md)."""
        return self.overlay.update_progress(value, stage)
    
    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription text."""
        self.overlay.update_transcription(text, is_final=is_final)
        
        if is_final:
            self.is_recording = False
            # Restore menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = None  # Default icon
    
    def stop_recording(self):
        """Stop recording and hide status bar indication."""
        if self.is_recording:
            self.is_recording = False
            self.overlay.stop_recording()
            
            # Restore menu bar icon if available
            if self.rumps_app and hasattr(self.rumps_app, 'icon'):
                self.rumps_app.icon = None  # Default icon
    
    def update_audio_levels(self, audio_data):
        """Placeholder for audio level updates (not needed for status bar)."""
        pass
    
    def cleanup(self):
        """Cleanup resources."""
        self.overlay.cleanup()


# For backward compatibility, alias the manager classes
UIManager = StreamingOverlayManager


if __name__ == "__main__":
    def test_status_bar_system():
        """Test the status bar-based overlay system."""
        manager = StreamingOverlayManager()
        
        try:
            print("Testing native status bar system...")
            print("👀 Look for status bar icons in your macOS menu bar!")
            
            # Start recording
            manager.start_recording()
            time.sleep(1)
            
            # Show processing stages
            manager.show_processing("Transcribing")
            time.sleep(1)
            
            manager.update_progress(25, "Segmenting")
            time.sleep(1)
            
            manager.update_progress(50, "Processing")
            time.sleep(1)
            
            manager.update_progress(75, "Punctuation")
            time.sleep(1)
            
            # Simulate streaming updates
            test_phrases = [
                "Hello",
                "Hello world",
                "Hello world this is",
                "Hello world this is a test",
                "Hello world this is a test of the status bar system."
            ]
            
            for i, phrase in enumerate(test_phrases):
                is_final = (i == len(test_phrases) - 1)
                manager.update_transcription(phrase, is_final=is_final)
                time.sleep(0.5)
            
            print("Test completed!")
            
        except KeyboardInterrupt:
            print("Test interrupted")
        finally:
            manager.cleanup()
    
    test_status_bar_system()