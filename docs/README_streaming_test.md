# AWS Transcribe Streaming Test

This document explains how to test AWS Transcribe Streaming speech-to-text integration and compare it with local Whisper models.

## Overview

The `streaming_transcribe_test.py` script provides real-time speech-to-text transcription using AWS Transcribe Streaming API, with performance comparison against local Whisper models.

## Key Features

- **Real-time transcription**: Stream audio directly to AWS Transcribe for immediate results
- **Low latency**: Get partial results as you speak, with final results when speech segments complete
- **Performance comparison**: Side-by-side comparison with Whisper models
- **Flexible input**: Support for both microphone input and audio file streaming
- **Detailed metrics**: Real-time factor, first result latency, and accuracy measurements

## Prerequisites

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials**:
   ```bash
   aws configure
   ```
   Or set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-west-2
   ```

3. **Audio requirements**:
   - For file input: 16kHz, 16-bit, mono PCM WAV files
   - For microphone: Built-in microphone or USB audio device

## Usage Examples

### 1. Test with Microphone (Real-time)
```bash
python streaming_transcribe_test.py --source microphone --duration 10
```
This will:
- Record from your microphone for 10 seconds
- Stream audio to AWS Transcribe in real-time
- Show partial and final transcription results
- Display performance metrics

### 2. Test with Audio File
```bash
python streaming_transcribe_test.py --source file --audio-file sample.wav
```
This will:
- Stream the audio file to AWS Transcribe (simulating real-time)
- Compare results with Whisper transcription of the same file
- Show detailed performance comparison

### 3. Custom Configuration
```bash
python streaming_transcribe_test.py \
  --source file \
  --audio-file sample.wav \
  --whisper-model large \
  --region us-east-1 \
  --duration 15
```

## Command Line Options

- `--audio-file`: Path to audio file for testing (required for file source)
- `--duration`: Recording duration in seconds for microphone test (default: 10)
- `--whisper-model`: Whisper model size: tiny, base, small, medium, large (default: medium)
- `--region`: AWS region for Transcribe service (default: us-west-2)
- `--source`: Audio source: microphone or file (default: microphone)

## Performance Metrics

The script measures and compares:

1. **Real-time Factor (RTF)**:
   - < 1.0 = Faster than real-time
   - = 1.0 = Real-time processing
   - > 1.0 = Slower than real-time

2. **First Result Latency**: Time to receive first partial result (streaming only)

3. **Total Processing Time**: End-to-end processing duration

4. **Transcript Accuracy**: Word-level similarity comparison

## Expected Results

### AWS Transcribe Streaming Advantages:
- **Low latency**: First results typically within 1-2 seconds
- **Real-time processing**: RTF usually < 0.5x
- **Immediate feedback**: Partial results as you speak
- **No file size limits**: Can handle continuous streams

### Whisper Advantages:
- **Higher accuracy**: Especially for complex audio or accents
- **Offline processing**: No internet required
- **Consistent performance**: No network dependency
- **Better punctuation**: More natural text formatting

## Troubleshooting

### Common Issues:

1. **AWS Credentials Error**:
   ```
   Solution: Run 'aws configure' or set environment variables
   ```

2. **Audio Format Error**:
   ```
   Error: Audio file must be mono, 16-bit PCM
   Solution: Convert audio using: ffmpeg -i input.wav -ar 16000 -ac 1 -sample_fmt s16 output.wav
   ```

3. **Microphone Permission**:
   ```
   Solution: Grant microphone access to your terminal/Python
   ```

4. **Network Issues**:
   ```
   Solution: Check internet connection and AWS service status
   ```

## Sample Output

```
==================================================
AWS TRANSCRIBE STREAMING TEST
==================================================
Starting microphone recording for 10 seconds...
Speak now!
[PARTIAL] Hello
[PARTIAL] Hello world
[FINAL] Hello world, this is a test.
[PARTIAL] How are
[PARTIAL] How are you
[FINAL] How are you today?

STREAMING RESULTS:
Transcript: Hello world, this is a test. How are you today?
Audio Duration: 8.50s
Total Processing Time: 9.20s
First Result Latency: 1.20s
Real-time Factor: 1.08x

==================================================
WHISPER COMPARISON TEST
==================================================
Transcript: Hello world, this is a test. How are you today?
Audio Duration: 8.50s
Processing Time: 12.30s
Real-time Factor: 1.45x

============================================================
PERFORMANCE COMPARISON
============================================================
Metric                    Streaming       Whisper         Winner
------------------------------------------------------------
Real-time Factor          1.08           1.45            Streaming
First Result Latency     1.20           N/A             Streaming

Transcript Comparison:
Streaming: Hello world, this is a test. How are you today?
Whisper:   Hello world, this is a test. How are you today?
Word Similarity: 100.0%
```

## Integration with Existing Dictation System

This streaming test can be integrated with the existing `whisper_dictation.py` system by:

1. Adding streaming as a transcription provider option
2. Implementing real-time feedback in the UI
3. Using streaming for live dictation and Whisper for file processing
4. Creating a hybrid approach that uses streaming for immediate feedback and Whisper for final accuracy

## Next Steps

1. Test with various audio qualities and accents
2. Measure performance under different network conditions
3. Implement error handling and reconnection logic
4. Consider hybrid approaches combining both methods
5. Integrate streaming capabilities into the main dictation system