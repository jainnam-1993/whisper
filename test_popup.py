#!/usr/bin/env python3
"""
Test script for Recording Popup GUI
Run this to test the popup functionality independently
"""

import sys
import time
import threading
sys.path.append('src')

def test_popup():
    """Test the recording popup functionality"""
    
    print("🧪 Testing Recording Popup...")
    
    try:
        from src.gui.recording_popup import show_recording_popup, hide_recording_popup, is_recording_popup_visible
        
        # Test callbacks
        def on_stop():
            print("🔴 Stop button clicked!")
            hide_recording_popup()
        
        def on_cancel():
            print("❌ Cancel button clicked!")
            hide_recording_popup()
        
        # Show popup with callbacks
        print("📱 Showing popup...")
        show_recording_popup(stop_callback=on_stop, cancel_callback=on_cancel)
        
        # Verify popup is visible
        if is_recording_popup_visible():
            print("✅ Popup is visible")
        else:
            print("❌ Popup failed to show")
            return False
        
        # Keep popup open for 10 seconds for manual testing
        print("⏰ Popup will auto-close in 10 seconds (or click Stop/Cancel to test callbacks)")
        for i in range(10):
            if not is_recording_popup_visible():
                print("✅ Popup was closed by user interaction")
                return True
            print(f"⏳ {10-i} seconds remaining...")
            time.sleep(1)
        
        # Auto-close after 10 seconds
        print("⏰ Auto-closing popup...")
        hide_recording_popup()
        
        # Verify popup is hidden
        time.sleep(0.5)
        if not is_recording_popup_visible():
            print("✅ Popup successfully hidden")
            return True
        else:
            print("❌ Popup failed to hide")
            return False
            
    except Exception as e:
        print(f"❌ Error testing popup: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_audio_monitor():
    """Test the audio monitoring functionality"""
    
    print("\n🧪 Testing Audio Monitor...")
    
    try:
        from src.utils.audio_monitor import create_audio_monitor
        
        levels_received = []
        
        def level_callback(level):
            levels_received.append(level)
            if len(levels_received) <= 5:  # Show first 5 levels
                print(f"🎵 Audio level: {level:.3f}")
        
        monitor = create_audio_monitor(callback=level_callback)
        
        if monitor.start_monitoring():
            print("🎤 Audio monitoring started...")
            print("💬 Try speaking or making noise for 5 seconds...")
            
            time.sleep(5)
            
            monitor.stop_monitoring()
            
            if levels_received:
                avg_level = sum(levels_received) / len(levels_received)
                max_level = max(levels_received)
                print(f"✅ Received {len(levels_received)} audio level updates")
                print(f"📊 Average level: {avg_level:.3f}, Max level: {max_level:.3f}")
                return True
            else:
                print("❌ No audio levels received")
                return False
        else:
            print("❌ Failed to start audio monitoring")
            return False
            
    except Exception as e:
        print(f"❌ Error testing audio monitor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Test popup + audio monitor integration"""
    
    print("\n🧪 Testing Popup + Audio Monitor Integration...")
    
    try:
        from src.gui.recording_popup import RecordingPopupManager
        
        manager = RecordingPopupManager()
        
        def on_stop():
            print("🔴 Integration test: Stop clicked")
            manager.hide_recording_popup()
        
        def on_cancel():
            print("❌ Integration test: Cancel clicked")  
            manager.hide_recording_popup()
        
        manager.set_callbacks(stop_callback=on_stop, cancel_callback=on_cancel)
        
        print("📱 Showing popup with audio monitoring...")
        manager.show_recording_popup()
        
        if manager.is_popup_visible():
            print("✅ Integrated popup is visible")
            print("🎤 Audio monitoring should be active - try speaking!")
            print("⏰ Auto-closing in 8 seconds...")
            
            time.sleep(8)
            
            manager.hide_recording_popup()
            
            if not manager.is_popup_visible():
                print("✅ Integrated popup successfully hidden")
                return True
            else:
                print("❌ Failed to hide integrated popup")
                return False
        else:
            print("❌ Integrated popup failed to show")
            return False
            
    except Exception as e:
        print(f"❌ Error testing integration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Recording Popup Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test basic popup functionality
    results.append(("Basic Popup", test_popup()))
    
    # Test audio monitoring
    results.append(("Audio Monitor", test_audio_monitor()))
    
    # Test integration
    results.append(("Integration", test_integration()))
    
    # Print results
    print("\n📋 Test Results:")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    # Overall result
    all_passed = all(result[1] for result in results)
    overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    print(f"\nOverall: {overall_status}")
    
    sys.exit(0 if all_passed else 1)