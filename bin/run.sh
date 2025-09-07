#!/bin/bash
# Whisper service launcher with environment setup

# Set Picovoice access key for wake word detection (required for pvporcupine 3.0.5)
# This MUST be set before Python starts for subprocess inheritance
export PICOVOICE_ACCESS_KEY="lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=="

# Change to project directory and launch RealtimeSTT with wake word support
cd /Volumes/workplace/tools/whisper
exec ./.venv/bin/python3.13 -m src.services.keyboard_service "$@"