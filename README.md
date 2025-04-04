# Multilingual Dictation App based on OpenAI Whisper
Multilingual dictation app based on the powerful OpenAI Whisper ASR model(s) to provide accurate and efficient speech-to-text conversion in any application. The app runs in the background and is triggered through a keyboard shortcut. It is also entirely offline, so no data will be shared. It allows users to set up their own keyboard combinations and choose from different Whisper models, and languages.

## Prerequisites
The PortAudio and llvm library is required for this app to work. You can install it on macOS using the following command:

```bash
brew install portaudio llvm
```

## Permissions
The app requires accessibility permissions to register global hotkeys and permission to access your microphone for speech recognition.

## Installation
Clone the repository:

```bash
git clone https://github.com/foges/whisper-dictation.git
cd whisper-dictation
```

If you use poetry:

```shell
poetry install
poetry shell
```

Or, if you don't use poetry, first create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required packages:

```bash
# Option 1: Using requirements.txt
pip install -r requirements.txt

# Option 2: Install packages directly
pip install pyaudio numpy rumps pynput
pip install git+https://github.com/openai/whisper.git
```

## Usage
Run the application:

```bash
python whisper_dictation.py
```

By default, the app uses the "base" Whisper ASR model and the key combination to toggle dictation is cmd+option on macOS and ctrl+alt on other platforms. You can change the model and the key combination using command-line arguments.  Note that models other than `tiny` and `base` can be slow to transcribe and are not recommended unless you're using a powerful computer, ideally one with a CUDA-enabled GPU. For example:


```bash
python whisper_dictation.py -m large -k cmd_r+shift -l en
```

The models are multilingual, and you can specify a two-letter language code (e.g., "no" for Norwegian) with the `-l` or `--language` option. Specifying the language can improve recognition accuracy, especially for smaller model sizes.

#### Replace macOS default dictation trigger key
You can use this app to replace macOS built-in dictation. Trigger to begin recording with a double click of Right Command key and stop recording with a single click of Right Command key.
```bash
python whisper_dictation.py -m large --k_double_cmd -l en
```
To use this trigger, go to System Settings -> Keyboard, disable Dictation. If you double click Right Command key on any text field, macOS will ask whether you want to enable Dictation, so select Don't Ask Again.

## Setting the App as a Startup Item
To have the app run automatically when your computer starts, follow these steps:

 1. Open System Preferences.
 2. Go to Users & Groups.
 3. Click on your username, then select the Login Items tab.
 4. Click the + button and add the `run.sh` script from the whisper-dictation folder.

# Whisper Dictation

A dictation tool that uses OpenAI's Whisper model for speech-to-text transcription.

## Setup

The application has been set up to start automatically when you log in to your Mac.

### Key Commands

- **Double-click the Right Command key (⌘)** to start recording
- **Single-click the Right Command key (⌘)** to stop recording and transcribe

### Status Indicator

Look for the "⏯" icon in your menu bar. When recording, it will show a timer and a red dot.

## Managing the Service

### Check if the service is running

```bash
ps aux | grep -i whisper
```

### Start the service manually

```bash
launchctl start com.user.whisper-dictation
```

### Stop the service

```bash
launchctl stop com.user.whisper-dictation
```

### Disable the service from starting at login

```bash
launchctl unload ~/Library/LaunchAgents/com.user.whisper-dictation.plist
```

### Enable the service to start at login

```bash
launchctl load ~/Library/LaunchAgents/com.user.whisper-dictation.plist
```

## Troubleshooting

### Accessibility Permissions

Make sure to grant accessibility permissions to the application:

1. Open System Settings (or System Preferences)
2. Go to Privacy & Security > Accessibility
3. Make sure Python.app is in the list and checked

### Logs

Check the logs for any errors:

```bash
cat /Volumes/Workspace/whisper-dictation/whisper-dictation.log
cat /Volumes/Workspace/whisper-dictation/whisper-dictation.err
```

## Configuration

To change settings, edit the `startup.sh` file and modify the command-line arguments.

Available options:
- `--model_name`: Choose the Whisper model (tiny, base, small, medium, large)
- `--language`: Specify the language for better recognition
- `--max_time`: Maximum recording time in seconds (default: 30)

## Recent Improvements

### Resource Management

The application has been improved to better manage system resources:

* Enhanced cleanup of PyAudio streams to prevent resource leaks
* Proper management of multiprocessing resources and semaphores
* Thread synchronization using locks to prevent race conditions
* Context managers for resources that need proper cleanup

### Signal Handling

The application now includes robust signal handling to ensure graceful shutdown:

* Proper handling of SIGINT (Ctrl+C) and SIGTERM signals
* Graceful cleanup of resources when the application is interrupted
* Orderly shutdown sequence that ensures all resources are properly released
* Prevention of segmentation faults during termination

### Stability Enhancements

The application has undergone extended run testing to ensure stability:

* Tested for long recording sessions without resource leaks
* Verified proper cleanup on all termination paths
* Eliminated segmentation faults that occurred in previous versions
* Improved error handling throughout the codebase

To test the stability yourself, run the application for an extended period with various recording sessions:

```bash
python whisper_dictation.py --model_name base --max_time 120
```

Start and stop recording multiple times, then exit with Ctrl+C to verify proper cleanup.

# Whisper Dictation Service

A robust service wrapper for running the Whisper dictation system with automatic crash recovery and system startup integration.

## Features

- Automatic startup on system login
- Immediate crash recovery
- GPU memory optimization
- Clean process management
- Simple control interface

## Service Architecture

The service consists of three main components:

1. **Core Service (`whisper_service.py`)**
   - Monitors the Whisper process health
   - Provides immediate restart on crashes
   - Optimizes GPU memory usage
   - Handles process signals gracefully

2. **Control Interface (`manage_whisper.py`)**
   - Provides commands to start/stop/restart the service
   - Shows service status
   - Manages process lifecycle

3. **Auto-startup Integration (`com.whisper.service.plist`)**
   - Ensures service starts on system login
   - Maintains service availability
   - Handles logging

## Auto-reload Mechanism

The service implements a robust auto-reload mechanism:

1. **Continuous Monitoring**
   - Checks process status every second
   - Detects crashes through process exit codes
   - Identifies abnormal terminations

2. **Immediate Recovery**
   - Restarts the process immediately upon any failure
   - No artificial delays between restarts
   - Preserves GPU memory settings across restarts

3. **Resource Management**
   - Optimizes GPU memory allocation (512MB split size)
   - Cleans up process resources on shutdown
   - Maintains clean process hierarchy

## Installation

1. Create log directory:
```bash
sudo mkdir -p /var/log/whisper
sudo chown $USER /var/log/whisper
```

2. Install the LaunchAgent:
```bash
# Copy the launch agent to your user's LaunchAgents directory
cp com.whisper.service.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.whisper.service.plist
```

## Usage

The service can be controlled using the management script:

```bash
# Start the service
./manage_whisper.py start

# Check service status
./manage_whisper.py status

# Stop the service
./manage_whisper.py stop

# Restart the service
./manage_whisper.py restart
```

## Monitoring

Logs are available at:
- Main log: `/var/log/whisper/whisper.log`
- Error log: `/var/log/whisper/whisper.error.log`

## Troubleshooting

1. If the service fails to start:
   - Check the error log
   - Verify Python environment
   - Ensure correct file permissions

2. If the service crashes frequently:
   - Monitor GPU memory usage
   - Check system resources
   - Review error logs for patterns
