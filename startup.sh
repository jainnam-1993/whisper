#!/bin/bash

# Set the working directory
cd "$(dirname "$0")"

# Check if we should use Docker (default) or direct execution
USE_DOCKER=true

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --no-docker) USE_DOCKER=false; shift ;;
        *) shift ;;
    esac
done

if $USE_DOCKER; then
    # Make sure the Docker startup script is executable
    chmod +x docker-startup.sh
    chmod +x host_key_listener.py
    
    # Kill any existing host key listener processes
    echo "Stopping any existing key listener processes..."
    pkill -f host_key_listener.py 2>/dev/null || true
    
    # Check if sox is installed (needed for audio recording)
    if ! command -v rec &> /dev/null; then
        echo "Sox is not installed. Please install it for audio recording."
        echo "On macOS: brew install sox"
        echo "On Linux: sudo apt-get install sox"
        exit 1
    fi
    
    # Check if host_env virtual environment exists
    if [ ! -d "host_env" ]; then
        echo "Creating virtual environment for host key listener..."
        python3 -m venv host_env
        source host_env/bin/activate
        pip install pynput
        deactivate
    fi
    
    # Start Docker container
    ./docker-startup.sh
    
    # Wait a moment for Docker to initialize
    sleep 2
    
    # Start the host-side key listener using the virtual environment
    source host_env/bin/activate
    python3 host_key_listener.py > "$(dirname "$0")/host-listener.log" 2>&1 &
    deactivate
    
    echo "Started Whisper with Docker support."
    echo "Double-press Right Command key to start dictation"
    echo "Single-press Right Command key to stop and transcribe"
else
    # Make sure run.sh is executable
    chmod +x run.sh

    # Use the whisper_env virtual environment
    VENV_PYTHON="$(dirname "$0")/whisper_env/bin/python"

    # Run the script directly with Python instead of through a terminal
    "$VENV_PYTHON" whisper_dictation.py --model_name small.en --k_double_cmd > "$(dirname "$0")/whisper-dictation.log" 2>&1 & 
fi 
