#!/usr/bin/env python3
"""
Live popup test - shows the popup and keeps it open for voice testing
"""

import sys
import time
import threading
sys.path.append('src')

def live_test():
    """Show popup and keep it open for voice testing"""
    
    print("🎤 LIVE POPUP TEST")
    print("=" * 50)
    print("📱 Showing popup now...")
    print("🗣️  SPEAK into your microphone to see waveform react!")
    print("🔴 The waveform bars should change height and color when you speak")
    print("🟢 Green bars = loud voice")
    print("🔘 Gray bars = quiet voice") 
    print("⚪ Light bars = silence")
    print("")
    print("⏰ Popup will stay open for 30 seconds")
    print("💡 Or click 'Done'/'Cancel' buttons to close")
    print("=" * 50)
    
    try:
        from src.gui.recording_popup import RecordingPopupManager
        
        manager = RecordingPopupManager()
        
        # Track if user closed popup manually
        popup_closed_manually = threading.Event()
        
        def on_done():
            print("\n✅ User clicked 'Done' button!")
            popup_closed_manually.set()
            manager.hide_recording_popup()
        
        def on_cancel():
            print("\n❌ User clicked 'Cancel' button!")
            popup_closed_manually.set()
            manager.hide_recording_popup()
        
        manager.set_callbacks(stop_callback=on_done, cancel_callback=on_cancel)
        
        # Show popup with audio monitoring
        manager.show_recording_popup()
        
        if manager.is_popup_visible():
            print("✅ Popup is now visible!")
            print("🎤 Audio monitoring is active")
            print("")
            
            # Wait for 30 seconds or until user closes popup
            for i in range(30):
                if popup_closed_manually.is_set():
                    print("✅ Popup was closed by user interaction")
                    return True
                    
                if not manager.is_popup_visible():
                    print("❌ Popup disappeared unexpectedly")
                    return False
                
                remaining = 30 - i
                print(f"⏳ {remaining} seconds remaining... (speak now to test waveform!)", end='\r')
                time.sleep(1)
            
            print("\n⏰ 30 seconds elapsed - closing popup...")
            manager.hide_recording_popup()
            
            print("✅ Live test completed!")
            return True
            
        else:
            print("❌ Popup failed to show")
            return False
            
    except Exception as e:
        print(f"❌ Error in live test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = live_test()
    if success:
        print("\n🎉 Live test successful!")
        print("💬 Did you see the waveform bars change when you spoke?")
    else:
        print("\n💥 Live test failed")