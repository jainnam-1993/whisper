FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    gcc \
    linux-headers-generic \
    file \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a simpler container requirements
RUN echo "numpy\ntqdm\nopenai-whisper\nscipy" > /app/container-requirements.txt

# Install Python dependencies (without problematic packages)
RUN pip install --no-cache-dir -r container-requirements.txt

# Create a directory for models
RUN mkdir -p /app/models

# Copy application files
COPY whisper_dictation.py .
COPY run.sh .
RUN chmod +x run.sh

# Create a health check script
RUN echo '#!/bin/sh\npgrep -f "python whisper_headless.py" > /dev/null || exit 1' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Create a transcription script
RUN echo '#!/usr/bin/env python\n\
import sys\n\
import os\n\
import shutil\n\
import numpy as np\n\
import time\n\
import subprocess\n\
import traceback\n\
\n\
def load_whisper_model(model_name):\n\
    # Import here to avoid loading if not needed\n\
    from whisper import load_model\n\
    \n\
    # Try up to 3 times to load the model\n\
    attempts = 0\n\
    while attempts < 3:\n\
        try:\n\
            # Clear any cached versions with checksum errors\n\
            if os.path.exists(os.path.expanduser("~/.cache/whisper")):\n\
                print("Clearing whisper cache...")\n\
                shutil.rmtree(os.path.expanduser("~/.cache/whisper"))\n\
                \n\
            return load_model(model_name)\n\
        except Exception as e:\n\
            attempts += 1\n\
            print(f"Error loading model (attempt {attempts}/3): {e}")\n\
            time.sleep(1)  # Wait before retrying\n\
            \n\
    raise Exception("Failed to load model after 3 attempts")\n\
\n\
def check_audio_file(file_path):\n\
    """Check if the audio file is valid and print debug info"""\n\
    print(f"Checking audio file: {file_path}")\n\
    file_size = os.path.getsize(file_path)\n\
    print(f"File size: {file_size} bytes")\n\
    \n\
    try:\n\
        # Check file type using file command\n\
        file_cmd = subprocess.run(["file", file_path], capture_output=True, text=True)\n\
        print(f"File type: {file_cmd.stdout}")\n\
        \n\
        # Check audio details using ffprobe\n\
        ffprobe_cmd = subprocess.run(\n\
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,sample_rate", "-of", "default=noprint_wrappers=1", file_path],\n\
            capture_output=True, text=True\n\
        )\n\
        print(f"FFprobe info: {ffprobe_cmd.stdout}")\n\
    except Exception as e:\n\
        print(f"Error checking file details: {e}")\n\
    \n\
    # Return True if file size is reasonable\n\
    return file_size > 1000  # More than 1KB\n\
\n\
def convert_to_compatible_format(input_file, output_file):\n\
    """Convert audio to a format known to work well with Whisper"""\n\
    try:\n\
        cmd = [\n\
            "ffmpeg", "-y", "-i", input_file,\n\
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-hide_banner",\n\
            output_file\n\
        ]\n\
        print("Running conversion: " + " ".join(cmd))\n\
        proc = subprocess.run(cmd, capture_output=True, text=True)\n\
        \n\
        if proc.returncode != 0:\n\
            print(f"Conversion error: {proc.stderr}")\n\
            return False\n\
        \n\
        print("Conversion successful")\n\
        return True\n\
    except Exception as e:\n\
        print(f"Error in conversion: {e}")\n\
        traceback.print_exc()\n\
        return False\n\
\n\
def transcribe_file(file_path):\n\
    if not check_audio_file(file_path):\n\
        raise ValueError(f"Audio file is too small or invalid: {file_path}")\n\
    \n\
    # Convert to a compatible format\n\
    converted_file = "/tmp/converted_audio.wav"\n\
    if not convert_to_compatible_format(file_path, converted_file):\n\
        raise ValueError("Failed to convert audio to compatible format")\n\
        \n\
    model = load_whisper_model("small.en")\n\
    print("Model loaded for transcription")\n\
    \n\
    try:\n\
        result = model.transcribe(converted_file)\n\
        print(f"Raw transcription result: {result}")\n\
        return result["text"]\n\
    except Exception as e:\n\
        print(f"Error during transcription: {e}")\n\
        traceback.print_exc()\n\
        # Try once more with original file\n\
        try:\n\
            print("Retrying with original file...")\n\
            result = model.transcribe(file_path)\n\
            print(f"Raw transcription result: {result}")\n\
            return result["text"]\n\
        except Exception as e2:\n\
            print(f"Error during retry: {e2}")\n\
            traceback.print_exc()\n\
            raise\n\
\n\
if __name__ == "__main__":\n\
    try:\n\
        if len(sys.argv) > 1:\n\
            file_path = sys.argv[1]\n\
            if os.path.exists(file_path):\n\
                try:\n\
                    text = transcribe_file(file_path)\n\
                    print(f"Final transcription: {text}")\n\
                    \n\
                    # If transcription is empty but no error was raised\n\
                    if not text.strip():\n\
                        text = "No speech detected. Please speak clearly and try again."\n\
                        \n\
                    # Save the transcription to a file\n\
                    with open("/app/last_transcription.txt", "w") as f:\n\
                        f.write(text)\n\
                except Exception as e:\n\
                    error_msg = f"Error transcribing: {e}"\n\
                    print(error_msg, file=sys.stderr)\n\
                    traceback.print_exc()\n\
                    # Write error to transcription file\n\
                    with open("/app/last_transcription.txt", "w") as f:\n\
                        f.write("Transcription error. Please try again.")\n\
            else:\n\
                error_msg = f"File not found: {file_path}"\n\
                print(error_msg, file=sys.stderr)\n\
                with open("/app/last_transcription.txt", "w") as f:\n\
                    f.write(error_msg)\n\
        else:\n\
            error_msg = "No file path provided"\n\
            print(error_msg, file=sys.stderr)\n\
            with open("/app/last_transcription.txt", "w") as f:\n\
                f.write(error_msg)\n\
    except Exception as e:\n\
        print(f"Unhandled exception: {e}")\n\
        traceback.print_exc()\n\
        with open("/app/last_transcription.txt", "w") as f:\n\
            f.write("An unexpected error occurred.")\n\
' > /app/transcribe.py && chmod +x /app/transcribe.py

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD [ "/app/healthcheck.sh" ]

# Set restart policy
ENV PYTHONUNBUFFERED=1

# Create a headless version script for container use
RUN echo '#!/usr/bin/env python\n\
import sys\n\
import os\n\
import shutil\n\
import time\n\
import numpy as np\n\
import traceback\n\
\n\
def load_whisper_model(model_name):\n\
    # Import here to avoid loading if not needed\n\
    from whisper import load_model\n\
    \n\
    # Try up to 3 times to load the model\n\
    attempts = 0\n\
    while attempts < 3:\n\
        try:\n\
            # Clear any cached versions with checksum errors\n\
            if os.path.exists(os.path.expanduser("~/.cache/whisper")):\n\
                print("Clearing whisper cache...")\n\
                shutil.rmtree(os.path.expanduser("~/.cache/whisper"))\n\
                \n\
            return load_model(model_name)\n\
        except Exception as e:\n\
            attempts += 1\n\
            print(f"Error loading model (attempt {attempts}/3): {e}")\n\
            time.sleep(1)  # Wait before retrying\n\
            \n\
    raise Exception("Failed to load model after 3 attempts")\n\
\n\
def main():\n\
    print("Starting headless Whisper service...")\n\
    try:\n\
        model = load_whisper_model("small.en")\n\
        print("Model loaded successfully. Running transcription service.")\n\
    except Exception as e:\n\
        print(f"Error loading model: {e}")\n\
        traceback.print_exc()\n\
    # Keep container running\n\
    while True:\n\
        time.sleep(60)\n\
\n\
if __name__ == "__main__":\n\
    try:\n\
        main()\n\
    except Exception as e:\n\
        print(f"Unhandled exception in main: {e}")\n\
        traceback.print_exc()\n\
        # Sleep and then exit with error code to trigger container restart\n\
        time.sleep(10)\n\
        sys.exit(1)\n\
' > /app/whisper_headless.py

# Command to run the headless version in container
CMD ["python", "whisper_headless.py"] 