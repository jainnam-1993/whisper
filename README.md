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
pip install -r requirements.txt
```

## Usage
Run the application:

```bash
python whisper-dictation.py
```

By default, the app uses the "base" Whisper ASR model and the key combination to toggle dictation is cmd+option on macOS and ctrl+alt on other platforms. You can change the model and the key combination using command-line arguments.  Note that models other than `tiny` and `base` can be slow to transcribe and are not recommended unless you're using a powerful computer, ideally one with a CUDA-enabled GPU. For example:


```bash
python whisper-dictation.py -m large -k cmd_r+shift -l en
```

The models are multilingual, and you can specify a two-letter language code (e.g., "no" for Norwegian) with the `-l` or `--language` option. Specifying the language can improve recognition accuracy, especially for smaller model sizes.

#### Replace macOS default dictation trigger key
You can use this app to replace macOS built-in dictation. Trigger to begin recording with a double click of Right Command key and stop recording with a single click of Right Command key.
```bash
python whisper-dictation.py -m large --k_double_cmd -l en
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
