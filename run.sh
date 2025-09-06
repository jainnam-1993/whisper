#!/bin/bash
# Whisper service launcher with environment setup

# Set Picovoice access key for wake word detection (required for pvporcupine 3.0.5)
# This MUST be set before Python starts for subprocess inheritance
export PICOVOICE_ACCESS_KEY="lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=="

# Launch the appropriate service based on first argument
if [ "$1" = "docker" ]; then
    # Legacy Docker mode
    exec python whisper_headless.py
else
    # Default: RealtimeSTT with wake word support
    exec /Volumes/workplace/tools/whisper/.venv/bin/python3.13 host_key_listener.py "$@"
fi