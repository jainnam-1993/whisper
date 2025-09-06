#!/usr/bin/env python3
"""
Test script for RealtimeSTT wake word detection
Tests voice activation with "Hey Computer" or other supported wake words
"""

import sys
import time
from RealtimeSTT import AudioToTextRecorder

def test_wake_word_detection():
    """Test RealtimeSTT wake word functionality"""
    
    # Supported wake words for pvporcupine backend
    supported_wake_words = [
        'alexa', 'americano', 'blueberry', 'bumblebee', 'computer', 
        'grapefruits', 'grasshopper', 'hey google', 'hey siri', 
        'jarvis', 'ok google', 'picovoice', 'porcupine', 'terminator'
    ]
    
    print("🎙️ RealtimeSTT Wake Word Detection Test")
    print("=" * 50)
    print(f"Supported wake words: {', '.join(supported_wake_words)}")
    print()
    
    # Test configuration options
    test_configs = [
        {
            'name': 'Computer Wake Word (Porcupine)',
            'config': {
                'model': 'tiny',  # Fast model for testing
                'language': 'en',
                'wake_words': 'computer',
                'wakeword_backend': 'pvporcupine',
                'wake_words_sensitivity': 0.6,
                'wake_word_timeout': 5.0,
                'wake_word_activation_delay': 0.0,
                'spinner': False,
                'enable_realtime_transcription': False,
            }
        },
        {
            'name': 'Hey Computer (Porcupine)',
            'config': {
                'model': 'tiny',
                'language': 'en',
                'wake_words': 'computer',  # Note: "hey computer" may not be directly supported
                'wakeword_backend': 'pvporcupine', 
                'wake_words_sensitivity': 0.7,
                'wake_word_timeout': 8.0,
                'spinner': False,
                'enable_realtime_transcription': False,
            }
        },
        {
            'name': 'OpenWakeWord Backend',
            'config': {
                'model': 'tiny',
                'language': 'en',
                'wakeword_backend': 'openwakeword',
                'wake_words_sensitivity': 0.6,
                'wake_word_timeout': 5.0,
                'spinner': False,
                'enable_realtime_transcription': False,
            }
        }
    ]
    
    for i, test in enumerate(test_configs, 1):
        print(f"\n🧪 Test {i}: {test['name']}")
        print("-" * 30)
        
        try:
            # Add callbacks for debugging
            def on_wake_word_detected():
                print("🚨 WAKE WORD DETECTED! Listening for speech...")
            
            def on_wake_word_timeout():
                print("⏰ Wake word timeout - going back to sleep")
            
            def on_wake_word_start():
                print(f"👂 Listening for wake word...")
            
            def on_recording_start():
                print("🔴 Recording started")
            
            def on_recording_stop():
                print("⏹️ Recording stopped")
            
            # Create recorder with test configuration
            config = test['config'].copy()
            config.update({
                'on_wakeword_detected': on_wake_word_detected,
                'on_wakeword_timeout': on_wake_word_timeout,
                'on_wakeword_detection_start': on_wake_word_start,
                'on_recording_start': on_recording_start,
                'on_recording_stop': on_recording_stop,
            })
            
            print(f"Initializing with config: {test['name']}")
            recorder = AudioToTextRecorder(**config)
            
            if 'wake_words' in config:
                print(f"Wake word: '{config['wake_words']}'")
                print(f"Say '{config['wake_words']}' then speak your message")
            else:
                print("Using OpenWakeWord - say any supported wake word")
            
            print("Press Ctrl+C to stop this test and try next configuration")
            print("Waiting for wake word...")
            
            # Start listening for wake word + transcription
            start_time = time.time()
            timeout = 30  # 30 second timeout per test
            
            while time.time() - start_time < timeout:
                try:
                    text = recorder.text()  # This should wait for wake word + speech
                    if text and text.strip():
                        print(f"✅ Transcribed: '{text.strip()}'")
                        break
                    else:
                        print("ℹ️ No speech detected after wake word")
                        
                except KeyboardInterrupt:
                    print("\n🛑 Test interrupted by user")
                    break
                    
            if time.time() - start_time >= timeout:
                print(f"⏰ Test timed out after {timeout} seconds")
            
        except Exception as e:
            print(f"❌ Error in test '{test['name']}': {e}")
            print(f"This might be due to missing dependencies or unsupported configuration")
        
        # Ask user if they want to continue
        if i < len(test_configs):
            try:
                response = input(f"\nTry next test? (y/n): ").strip().lower()
                if response not in ['y', 'yes', '']:
                    break
            except KeyboardInterrupt:
                print("\n🛑 Testing stopped by user")
                break
    
    print("\n🏁 Wake word testing complete!")

def test_simple_wake_word():
    """Simple wake word test with minimal configuration"""
    
    print("\n🎯 Simple Wake Word Test")
    print("=" * 30)
    
    try:
        print("Creating recorder with 'computer' wake word...")
        
        recorder = AudioToTextRecorder(
            model='tiny',
            language='en',
            wake_words='computer',
            wakeword_backend='pvporcupine',
            wake_words_sensitivity=0.6,
            wake_word_timeout=10.0,
            spinner=False,
            enable_realtime_transcription=False,
        )
        
        print("✅ Recorder initialized successfully")
        print("\n📢 Instructions:")
        print("1. Say 'computer' to activate")
        print("2. Then speak your message")  
        print("3. Press Ctrl+C to exit")
        print("\nListening...")
        
        while True:
            try:
                text = recorder.text()
                if text and text.strip():
                    print(f"✅ You said: '{text.strip()}'")
                else:
                    print("ℹ️ No speech detected")
                    
            except KeyboardInterrupt:
                print("\n🛑 Exiting...")
                break
                
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install required packages: pip install pvporcupine")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎙️ RealtimeSTT Wake Word Detection Testing")
    print("This script tests voice activation capabilities")
    print()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--simple':
            test_simple_wake_word()
        else:
            test_wake_word_detection()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Try running with --simple flag for basic test")