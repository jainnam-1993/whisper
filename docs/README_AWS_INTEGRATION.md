# AWS Transcribe Integration

This document describes the AWS Transcribe integration added to the Whisper dictation application.

## Overview

The application now supports two transcription backends:
1. **Local Whisper Models** (default) - Complete offline processing
2. **AWS Transcribe** (optional) - Cloud-based transcription service

## Usage

### Using Local Whisper (Default)
```bash
python whisper_dictation.py
```

### Using AWS Transcribe
```bash
python whisper_dictation.py --use_aws_transcribe
```

### Additional AWS Options
```bash
# Specify AWS region
python whisper_dictation.py --use_aws_transcribe --aws_region us-west-2

# Use with specific language
python whisper_dictation.py --use_aws_transcribe -l en
```

## Prerequisites for AWS Transcribe

1. **Install Dependencies**
   ```bash
   pip install boto3 amazon-transcribe
   ```

2. **Configure AWS Credentials**
   
   Option 1: AWS CLI
   ```bash
   aws configure
   ```
   
   Option 2: Environment Variables
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```
   
   Option 3: IAM Role (for EC2 instances)

3. **Required AWS Permissions**
   Your AWS credentials need the following permissions:
   - `transcribe:StartStreamTranscription`

## Architecture

### New Components

- **`transcription_service.py`** - Abstract transcription service interface
  - `TranscriptionService` - Base abstract class
  - `WhisperTranscriptionService` - Local Whisper implementation
  - `AWSTranscriptionService` - AWS Transcribe streaming implementation

### Key Features

- **Feature Flag Architecture** - Choose transcription backend via command line
- **Unified Interface** - Same user experience regardless of backend
- **Resource Management** - No local model loading when using AWS
- **Error Handling** - Graceful fallback and clear error messages
- **Language Support** - Automatic language code mapping between services

### User Experience

The keyboard shortcuts and recording behavior remain identical:
- Double Command key press to start/stop recording (macOS)
- Same status bar interface
- Same text typing behavior

## Benefits

### Local Whisper
- ✅ Complete privacy (offline processing)
- ✅ No ongoing costs
- ✅ No internet dependency
- ❌ Slower startup (model loading)
- ❌ Uses local compute resources

### AWS Transcribe
- ✅ Fast startup (no model loading)
- ✅ Potentially faster transcription
- ✅ No local compute usage
- ❌ Requires internet connection
- ❌ Usage-based pricing
- ❌ Data sent to AWS

## Troubleshooting

### AWS Transcribe Issues

1. **"Failed to initialize AWS Transcribe client"**
   - Check AWS credentials configuration
   - Verify internet connectivity
   - Ensure correct region setting

2. **"amazon-transcribe is required"**
   ```bash
   pip install amazon-transcribe
   ```

3. **"boto3 is required"**
   ```bash
   pip install boto3
   ```

4. **Permission errors**
   - Verify IAM permissions for Transcribe service
   - Check AWS credentials are properly configured

### General Issues

1. **Import errors**
   - Ensure all dependencies are installed
   - Check Python environment

2. **Audio issues**
   - Same troubleshooting as original Whisper setup
   - Check microphone permissions

## Implementation Details

The integration uses AWS Transcribe's streaming API to maintain the same batch-processing user experience as local Whisper. Audio is collected during recording and then sent to AWS Transcribe for processing, maintaining the familiar "record then transcribe" workflow.

The streaming implementation provides better performance than the batch API while still preserving the existing user interface patterns.