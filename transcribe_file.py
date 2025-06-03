#!/usr/bin/env python3
import argparse
import whisper
import os
import time

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file using Whisper")
    parser.add_argument("audio_file", help="Path to the audio file to transcribe")
    parser.add_argument("-m", "--model", default="base", choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model to use (default: base)")
    parser.add_argument("-l", "--language", default=None, 
                        help="Language code (e.g., 'en' for English). If not specified, Whisper will auto-detect.")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file path (default: same as input with .txt extension)")
    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        return 1

    # Set output file if not specified
    if args.output is None:
        base_name = os.path.splitext(args.audio_file)[0]
        args.output = f"{base_name}.txt"

    print(f"Loading Whisper model: {args.model}...")
    start_time = time.time()
    model = whisper.load_model(args.model)
    print(f"Model loaded in {time.time() - start_time:.2f} seconds")

    print(f"Transcribing {args.audio_file}...")
    start_time = time.time()
    
    # Set transcription options
    options = {}
    if args.language:
        options["language"] = args.language
    
    # Perform transcription
    result = model.transcribe(args.audio_file, **options)
    
    print(f"Transcription completed in {time.time() - start_time:.2f} seconds")
    
    # Write output to file
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    print(f"Transcription saved to: {args.output}")
    return 0

if __name__ == "__main__":
    exit(main())
