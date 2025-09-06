#!/usr/bin/env python3
"""
Direct Jarvis Wake Word Service
Simple script using RealtimeSTT with built-in wake word detection
Configuration via environment variables
"""

import os
import time
import traceback
from RealtimeSTT import AudioToTextRecorder


class ClipboardManager:
    """Simple clipboard management for auto-paste workflow"""
    
    def __init__(self):
        self.original_clipboard = None
    
    def preserve_clipboard(self):
        """Save current clipboard content"""
        try:
            import subprocess
            result = subprocess.run(['pbpaste'], capture_output=True, text=True)
            self.original_clipboard = result.stdout
        except Exception as e:
            print(f"Warning: Could not preserve clipboard: {e}")
            self.original_clipboard = None
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        try:
            import subprocess
            subprocess.run(['pbcopy'], input=text, text=True)
            return True
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            return False
    
    def paste_from_clipboard(self):
        """Paste from clipboard using keyboard shortcut"""
        try:
            import subprocess
            # Use AppleScript for reliable paste
            applescript = '''
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            subprocess.run(['osascript', '-e', applescript])
            return True
        except Exception as e:
            print(f"Error pasting: {e}")
            return False
    
    def restore_clipboard(self):
        """Restore original clipboard content"""
        if self.original_clipboard is not None:
            try:
                import subprocess
                subprocess.run(['pbcopy'], input=self.original_clipboard, text=True)
            except Exception as e:
                print(f"Warning: Could not restore clipboard: {e}")


def main():
    """Main Jarvis service loop"""
    
    # Environment configuration
    WAKE_WORD = os.getenv('WAKE_WORD', 'jarvis')
    MODEL_NAME = os.getenv('MODEL_NAME', 'base')
    LANGUAGE = os.getenv('LANGUAGE', 'en') 
    PRE_BUFFER = float(os.getenv('PRE_BUFFER_DURATION', '2.0'))
    VAD_SENSITIVITY = float(os.getenv('VAD_SENSITIVITY', '0.4'))
    
    print("🚀 Starting Jarvis Wake Word Service")
    print(f"📋 Configuration:")
    print(f"   Wake Word: {WAKE_WORD}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Language: {LANGUAGE}")
    print(f"   Pre-buffer: {PRE_BUFFER}s")
    print(f"   VAD Sensitivity: {VAD_SENSITIVITY}")
    
    # Initialize clipboard manager
    clipboard = ClipboardManager()
    
    try:
        # Direct RealtimeSTT initialization - no wrapper needed
        recorder = AudioToTextRecorder(
            model=MODEL_NAME,
            language=LANGUAGE,
            wake_words=WAKE_WORD,
            wakeword_backend="pvporcupine",
            enable_realtime_transcription=True,
            pre_recording_buffer_duration=PRE_BUFFER,
            silero_sensitivity=VAD_SENSITIVITY,
            webrtc_sensitivity=3,
            post_speech_silence_duration=0.4,
            min_length_of_recording=0.3,
            spinner=False
        )
        
        print(f"✅ Jarvis service initialized successfully!")
        print(f"🗣️ Say '{WAKE_WORD}' then speak your dictation...")
        print("Press Ctrl+C to stop")
        
        # Main service loop
        while True:
            try:
                # Wait for wake word + transcription
                text = recorder.text()
                
                if text and text.strip():
                    print(f"📝 Transcription: {text}")
                    
                    # Auto-paste workflow
                    clipboard.preserve_clipboard()
                    time.sleep(0.1)
                    
                    if clipboard.copy_to_clipboard(text):
                        time.sleep(0.2)
                        if clipboard.paste_from_clipboard():
                            time.sleep(0.2)
                            clipboard.restore_clipboard()
                            print(f"✅ Auto-pasted successfully")
                        else:
                            print("⚠️ Auto-paste failed - text copied to clipboard")
                    else:
                        print("❌ Failed to copy text to clipboard")
                    
                    print(f"🗣️ Ready for next '{WAKE_WORD}' command...")
                
            except KeyboardInterrupt:
                print("\n🛑 Jarvis service stopping...")
                break
            except Exception as e:
                print(f"❌ Error processing wake word: {e}")
                traceback.print_exc()
                time.sleep(1)  # Brief pause before retry
                
    except Exception as e:
        print(f"❌ Failed to initialize Jarvis service: {e}")
        traceback.print_exc()
        return 1
    
    print("👋 Jarvis service stopped")
    return 0


if __name__ == "__main__":
    exit(main())