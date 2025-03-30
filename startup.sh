#!/bin/bash

# Set the working directory
cd "$(dirname "$0")"

# Make sure run.sh is executable
chmod +x run.sh

# Use the whisper_env virtual environment
VENV_PYTHON="$(dirname "$0")/whisper_env/bin/python"

# Run the script directly with Python instead of through a terminal
"$VENV_PYTHON" whisper-dictation.py --model_name small.en --k_double_cmd > "$(dirname "$0")/whisper-dictation.log" 2>&1 & 
