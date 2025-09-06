#!/usr/bin/env python3
"""
Minimal whisper_dictation.py for Docker compatibility
This is a placeholder since the actual service now uses RealtimeSTT
"""

print("Docker container whisper_dictation.py loaded")
print("Note: Main transcription service now uses RealtimeSTT with Jarvis wake word")

# Keep container running
import time
while True:
    time.sleep(60)