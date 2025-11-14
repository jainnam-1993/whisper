#!/bin/bash
# Whisper service with auto-restart on audio device change
# Manual start version - no launchd required

cd /Volumes/workplace/tools/whisper || exit 1

export PICOVOICE_ACCESS_KEY="lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=="

echo "🚀 Starting Whisper with auto-restart..."
echo "📋 Main log: /tmp/whisper.log"
echo "⚠️  Error log: /tmp/whisper-errors.log (EOFErrors from RealtimeSTT cleanup)"

# Auto-restart loop
while true; do
    # Launch the service (blocks until exit)
    # Redirect stderr to separate file to keep main log clean
    ./.venv/bin/python3.13 -m src.services.keyboard_service 2>>/tmp/whisper-errors.log

    EXIT_CODE=$?

    # Exit code 0 = clean exit (audio device change) - restart immediately
    if [ $EXIT_CODE -eq 0 ]; then
        echo "🔄 Audio device changed - restarting in 1s..."
        sleep 1
        continue
    fi

    # Other exit codes - stop
    echo "❌ Service crashed with code $EXIT_CODE - exiting"
    break
done
