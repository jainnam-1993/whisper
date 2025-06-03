# Amazon Q Notes for Whisper Dictation

## Overview
This document contains notes and instructions for using Amazon Q with the Whisper Dictation application.

## Common Commands

### Check application status
```bash
ps aux | grep -i whisper
```

### Start/Stop Service
```bash
# Start the service
launchctl start com.user.whisper-dictation

# Stop the service
launchctl stop com.user.whisper-dictation
```

### Configuration Options
- Model options: tiny, base, small, medium, large
- Language can be specified with a two-letter code (e.g., "en" for English)
- Default keyboard shortcut: cmd+option (macOS) or ctrl+alt (other platforms)

## Troubleshooting
1. Check if microphone permissions are enabled
2. Verify accessibility permissions in System Settings
3. Check log files for errors
4. Ensure PortAudio and llvm are installed

## Example Commands
```bash
# Run with large model and English language
python whisper_dictation.py -m large -l en

# Run with custom keyboard shortcut
python whisper_dictation.py -k cmd_r+shift

# Replace macOS default dictation
python whisper_dictation.py -m large --k_double_cmd -l en
```
