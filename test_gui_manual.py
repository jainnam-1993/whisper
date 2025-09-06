#!/usr/bin/env python3
"""
Manual GUI test script - Test the GUI popup without wake word trigger
Run this to see the GUI in action with simulated real-time transcription
"""

import time
import threading
from ui_components import UIManager

def test_gui_with_simulated_transcription():
    """Test the GUI with simulated real-time text updates"""
    
    print("🧪 Starting GUI manual test...")
    print("📝 This will show a popup bar with simulated real-time transcription")
    
    # Create UI manager
    ui_manager = UIManager(None)
    
    # Start recording (shows GUI)
    print("🎯 Showing GUI popup...")
    ui_manager.start_recording()
    
    # Simulate real-time transcription updates
    test_phrases = [
        "The",
        "The quick",
        "The quick brown",
        "The quick brown fox",
        "The quick brown fox jumps",
        "The quick brown fox jumps over",
        "The quick brown fox jumps over the",
        "The quick brown fox jumps over the lazy",
        "The quick brown fox jumps over the lazy dog"
    ]
    
    print("🔄 Simulating real-time updates...")
    for i, phrase in enumerate(test_phrases):
        # Update with partial text (gray color)
        ui_manager.update_transcription(phrase, is_final=False)
        print(f"   Update {i+1}: {phrase}")
        time.sleep(0.3)  # Simulate typing speed
    
    # Final update (white color)
    print("✅ Showing final transcription...")
    final_text = "The quick brown fox jumps over the lazy dog."
    ui_manager.update_transcription(final_text, is_final=True)
    
    # Keep showing for 2 seconds
    time.sleep(2)
    
    # Hide GUI
    print("🔚 Hiding GUI...")
    ui_manager.stop_recording()
    
    print("✨ Test complete!")

def test_gui_with_audio_visualization():
    """Test GUI with audio visualization bars"""
    
    print("🎵 Testing with audio visualization...")
    
    # Create UI manager
    ui_manager = UIManager(None)
    
    # Start recording
    ui_manager.start_recording()
    
    # Simulate audio data
    import numpy as np
    
    def generate_audio_data():
        """Generate simulated audio data"""
        # Simulate 16kHz audio with 512 samples
        for _ in range(50):  # 50 updates
            # Random audio levels
            audio = np.random.randn(512) * 0.3
            # Add some frequency components
            t = np.linspace(0, 512/16000, 512)
            audio += np.sin(2 * np.pi * 440 * t) * 0.2  # 440Hz tone
            audio += np.sin(2 * np.pi * 880 * t) * 0.1  # 880Hz harmonic
            
            # Update audio levels
            ui_manager.update_audio_levels(audio.astype(np.float32))
            time.sleep(0.05)  # 20 FPS update rate
    
    # Run audio simulation in thread
    audio_thread = threading.Thread(target=generate_audio_data)
    audio_thread.start()
    
    # Simulate transcription
    ui_manager.update_transcription("Testing audio visualization...", is_final=False)
    
    # Wait for audio to finish
    audio_thread.join()
    
    # Final text
    ui_manager.update_transcription("Audio visualization test complete!", is_final=True)
    time.sleep(2)
    
    # Stop
    ui_manager.stop_recording()
    print("✅ Audio visualization test complete!")

if __name__ == "__main__":
    print("=" * 50)
    print("GUI MANUAL TEST")
    print("=" * 50)
    print()
    print("Choose test mode:")
    print("1. Test real-time transcription updates")
    print("2. Test with audio visualization")
    print("3. Run both tests")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        test_gui_with_simulated_transcription()
    elif choice == "2":
        test_gui_with_audio_visualization()
    elif choice == "3":
        test_gui_with_simulated_transcription()
        print("\n" + "=" * 50 + "\n")
        test_gui_with_audio_visualization()
    else:
        print("Invalid choice. Running test 1 by default.")
        test_gui_with_simulated_transcription()
    
    print("\n🏁 All tests complete!")