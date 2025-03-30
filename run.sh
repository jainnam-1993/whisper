#!/bin/bash
echo "$(dirname "$0")"
# Use the whisper_env virtual environment
SCRIPT_DIR="$(dirname "$0")"
VENV_PYTHON="$SCRIPT_DIR/whisper_env/bin/python"
"$VENV_PYTHON" whisper_dictation.py --k_double_cmd
