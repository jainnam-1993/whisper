#!/usr/bin/env python3
"""
Test the redesigned recording popup with gradient background and waveform
"""

import time
import threading
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gui.recording_popup import RecordingPopup
from utils.audio_monitor import MockAudioMonitor


def test_popup():
    """Test the recording popup with mock audio"""
    print("Testing MCP blocking...")

    # Create popup
    def on_stop():
        print("Stop callback triggered")

    def on_cancel():
        print("Cancel callback triggered")

    popup = RecordingPopup(
        on_stop_callback=on_stop,
        on_cancel_callback=on_cancel
    )

    # Create mock audio monitor with callback
    audio_monitor = MockAudioMonitor(callback=popup.update_audio_level)

    # Start audio monitoring
    audio_monitor.start_monitoring()

    # Show popup
    popup.show()

    print("Popup should be visible with:")
    print("✓ Gradient background (blue to purple)")
    print("✓ 'Speech Recording' title")
    print("✓ Dynamic waveform animation")
    print("✓ Timer counting up")
    print("✓ File name display")
    print("✓ Should NOT steal focus from other windows")
    print("✓ Should stay visible when clicking elsewhere")

    # Keep popup open for 10 seconds
    try:
        print("\nPopup will stay open for 10 seconds...")
        print("Try clicking on other windows - popup should stay visible")
        time.sleep(10)
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        audio_monitor.stop_monitoring()
        popup.hide()
        # Exit the Qt app if it was created
        if hasattr(popup, 'app') and popup.app:
            popup.app.quit()


if __name__ == "__main__":
    test_popup()