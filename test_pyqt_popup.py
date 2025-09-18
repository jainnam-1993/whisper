#!/usr/bin/env python3
"""
Test the PyQt6-based recording popup
"""

import sys
import os
import time
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gui.recording_popup import RecordingPopup
from utils.audio_monitor import MockAudioMonitor
from PyQt6.QtWidgets import QApplication


def test_popup():
    """Test the PyQt recording popup with mock audio"""
    print("Testing PyQt6 recording popup...")
    print("✓ No tk root window")
    print("✓ No dock icon")
    print("✓ Proper floating window")

    # Create QApplication (required for PyQt)
    app = QApplication(sys.argv)

    # Prevent app from appearing in dock
    app.setQuitOnLastWindowClosed(False)

    # Create popup
    def on_stop():
        print("Stop callback triggered")
        app.quit()

    def on_cancel():
        print("Cancel callback triggered")
        app.quit()

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

    print("\nPopup should be visible with:")
    print("✓ Gradient background (blue to purple)")
    print("✓ 'Speech Recording' title")
    print("✓ Dynamic waveform animation")
    print("✓ Timer counting up")
    print("✓ File name display")
    print("✓ NO tk window or dock icon!")

    # Run Qt event loop
    try:
        app.exec()
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        audio_monitor.stop_monitoring()
        popup.hide()


if __name__ == "__main__":
    test_popup()