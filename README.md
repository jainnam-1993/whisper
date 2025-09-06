# Whisper Dictation

A multilingual dictation app based on OpenAI's Whisper ASR model for accurate offline speech-to-text conversion. The app runs in the background and supports both keyboard shortcuts and **"Jarvis" wake word activation**, with multiple languages and Whisper models.

## 🗣️ **New Feature: Jarvis Wake Word**

This enhanced version includes **Jarvis wake word detection** powered by Picovoice Porcupine:

- **Say "Jarvis"** → Start speaking → Automatic transcription and paste
- **Double Right Command** → Backup keyboard trigger 
- **RealtimeSTT backend** → 0.24s transcription (vs 3-5s Docker)
- **Auto-paste functionality** → Seamless text insertion

### Quick Start with Wake Words
```bash
# Start the enhanced service with Jarvis wake word:
/Volumes/workplace/tools/whisper/.venv/bin/python3.13 host_key_listener.py

# Then simply say "Jarvis" followed by your text!
```

## 🚀 Quick Start

### Prerequisites
```bash
# macOS requirements
brew install portaudio llvm
```

### Installation
```bash
git clone https://github.com/foges/whisper-dictation.git
cd whisper-dictation

# Option 1: Using Poetry (recommended)
poetry install && poetry shell

# Option 2: Using pip
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Basic Usage
```bash
# Start with default settings (base model, cmd+option hotkey)
python whisper_dictation.py

# Advanced usage
python whisper_dictation.py -m large -k cmd_r+shift -l en --max_time 120
```

## 📋 Table of Contents

- [Features](#features)
- [Installation & Setup](#installation--setup)
- [Usage Guide](#usage-guide)
- [Service Management](#service-management)
- [Docker Deployment](#docker-deployment)
- [AWS Integration](#aws-integration)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## ✨ Features

- **Offline Processing**: No data sharing, completely local transcription
- **Multi-language Support**: Supports 99+ languages via Whisper models
- **Flexible Hotkeys**: Customizable keyboard shortcuts
- **Multiple Models**: Choose from tiny to large models based on your hardware
- **Service Integration**: Auto-start on login with crash recovery
- **Docker Support**: Containerized deployment with health monitoring
- **AWS Integration**: Optional AWS Transcribe streaming support
- **Unlimited Recording**: No artificial time limits (configurable)

## 🛠 Installation & Setup

### System Requirements
- macOS (primary support)
- Python 3.8+
- PortAudio and LLVM libraries
- Microphone and accessibility permissions

### Detailed Installation

1. **Install Dependencies**
   ```bash
   brew install portaudio llvm
   ```

2. **Clone and Setup**
   ```bash
   git clone https://github.com/foges/whisper-dictation.git
   cd whisper-dictation
   
   # Using Poetry
   poetry install
   poetry shell
   
   # Or using pip
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Grant Permissions**
   - **Accessibility**: System Settings → Privacy & Security → Accessibility → Add Python.app
   - **Microphone**: System Settings → Privacy & Security → Microphone → Add Python.app

4. **Test Installation**
   ```bash
   python whisper_dictation.py --model_name base
   ```

## 📖 Usage Guide

### Basic Controls

| Hotkey | Action |
|--------|--------|
| `Cmd+Option` (default) | Start/Stop recording |
| `Double Right Cmd` | Start recording (alternative) |
| `Single Right Cmd` | Stop recording (alternative) |

### Command Line Options

```bash
python whisper_dictation.py [OPTIONS]

Options:
  -m, --model_name     Whisper model: tiny, base, small, medium, large
  -l, --language       Language code (e.g., 'en', 'es', 'fr')
  -k, --key           Custom hotkey combination
  -t, --max_time      Recording time limit (default: unlimited)
  --k_double_cmd      Use double Right Cmd key trigger
```

### Model Selection Guide

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `tiny` | ~39MB | Fastest | Good | Quick notes, low-end hardware |
| `base` | ~74MB | Fast | Better | General use (recommended) |
| `small` | ~244MB | Medium | Good | Balanced performance |
| `medium` | ~769MB | Slow | Better | High accuracy needs |
| `large` | ~1550MB | Slowest | Best | Maximum accuracy, powerful hardware |

### Language Support

Specify language for better accuracy:
```bash
python whisper_dictation.py -l en    # English
python whisper_dictation.py -l es    # Spanish
python whisper_dictation.py -l fr    # French
python whisper_dictation.py -l de    # German
# ... supports 99+ languages
```

## 🔧 Service Management

### Auto-Start Setup

1. **Install Service**
   ```bash
   # Copy launch agent
   cp com.whisper.service.plist ~/Library/LaunchAgents/
   
   # Load service
   launchctl load ~/Library/LaunchAgents/com.whisper.service.plist
   ```

2. **Service Control**
   ```bash
   # Using management script
   ./manage_whisper.py start    # Start service
   ./manage_whisper.py stop     # Stop service  
   ./manage_whisper.py restart  # Restart service
   ./manage_whisper.py status   # Check status
   
   # Using launchctl directly
   launchctl start com.whisper.service
   launchctl stop com.whisper.service
   ```

### Service Features

- **Auto-Recovery**: Immediate restart on crashes
- **Health Monitoring**: Regular process health checks
- **Resource Management**: Optimized GPU memory usage (512MB)
- **Clean Shutdown**: Proper resource cleanup on termination

### Monitoring

- **Logs**: `/var/log/whisper/whisper.log`
- **Errors**: `/var/log/whisper/whisper.error.log`
- **Status**: Check menu bar for ⏯ icon with recording timer

## 🐳 Docker Deployment

### Quick Start
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f whisper
```

### Architecture

The Docker setup uses a hybrid approach:
- **Host**: Key listener (`host_key_listener.py`) handles hotkeys and clipboard
- **Container**: Whisper transcription service runs in isolated environment
- **Communication**: HTTP API between host and container

### Configuration

Edit `docker-compose.yml` for customization:
```yaml
environment:
  - WHISPER_MODEL=base
  - WHISPER_LANGUAGE=en
  - MAX_RECORDING_TIME=300
```

For detailed Docker setup, see [DOCKER.md](docs/DOCKER.md).

## ☁️ AWS Integration

### AWS Transcribe Streaming

Optional integration with AWS Transcribe for enhanced streaming capabilities:

```bash
# Install AWS dependencies
pip install boto3 amazon-transcribe

# Configure credentials
aws configure

# Run with AWS support
python whisper_dictation.py --use-aws-transcribe
```

### Setup Requirements

1. **AWS Credentials**: Configure via `aws configure` or IAM roles
2. **Permissions**: Transcribe streaming permissions required
3. **Region**: Set appropriate AWS region for optimal latency

For detailed AWS setup, see [AWS_INTEGRATION.md](docs/README_AWS_INTEGRATION.md).

## ⚙️ Configuration

### Environment Variables
```bash
export WHISPER_MODEL=base
export WHISPER_LANGUAGE=en
export MAX_RECORDING_TIME=0  # Unlimited
```

### Configuration Files
- `startup.sh`: Service startup configuration
- `com.whisper.service.plist`: Launch agent settings
- `docker-compose.yml`: Docker environment settings

### Advanced Settings

**GPU Memory Optimization**:
```bash
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
```

**Custom Hotkeys**:
```bash
python whisper_dictation.py -k "ctrl+shift+space"
```

## 🔍 Troubleshooting

### Common Issues

**1. Recording Not Starting**
```bash
# Check permissions
System Settings → Privacy & Security → Accessibility → Python.app ✓
System Settings → Privacy & Security → Microphone → Python.app ✓

# Check process
ps aux | grep whisper

# Check logs
cat /var/log/whisper/whisper.log
```

**2. Service Won't Start**
```bash
# Reload launch agent
launchctl unload ~/Library/LaunchAgents/com.whisper.service.plist
launchctl load ~/Library/LaunchAgents/com.whisper.service.plist

# Check service status
./manage_whisper.py status
```

**3. Poor Transcription Quality**
- Try larger model: `-m medium` or `-m large`
- Specify language: `-l en`
- Check microphone quality and background noise
- Ensure clear speech and proper distance from microphone

**4. High CPU/Memory Usage**
- Use smaller model: `-m tiny` or `-m base`
- Enable GPU acceleration if available
- Check for multiple running instances

### Log Locations
- **Service Logs**: `/var/log/whisper/whisper.log`
- **Error Logs**: `/var/log/whisper/whisper.error.log`
- **Docker Logs**: `docker-compose logs whisper`

### Getting Help

1. Check logs for specific error messages
2. Verify all permissions are granted
3. Test with minimal configuration
4. Check GitHub issues for similar problems

## 🔧 Development

### Project Structure
```
whisper-dictation/
├── whisper_dictation.py      # Main application
├── whisper_service.py        # Service wrapper
├── manage_whisper.py         # Management interface
├── transcription_service.py  # Transcription logic
├── host_key_listener.py      # Docker host integration
├── accessibility_utils.py    # macOS accessibility helpers
├── docker-compose.yml        # Docker configuration
└── docs/                     # Additional documentation
```

### Key Components

- **Core Engine**: OpenAI Whisper for speech recognition
- **GUI Framework**: rumps for macOS menu bar integration
- **Audio Processing**: PyAudio for microphone input
- **Service Management**: Custom crash recovery and monitoring
- **Clipboard Integration**: Multi-tier paste mechanism with fallbacks

### Recent Improvements

**Performance Optimizations** (Latest):
- ✅ Pre-warmed audio system eliminates recording delay
- ✅ Unlimited recording time (removed 30-second limit)
- ✅ Enhanced resource management and cleanup
- ✅ Improved threading and race condition handling

**Stability Enhancements**:
- Robust signal handling for graceful shutdown
- Memory leak prevention in PyAudio streams
- Thread synchronization with proper locking
- Context managers for resource cleanup

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the Whisper ASR model
- Contributors and community feedback
- macOS accessibility framework developers

---

**Status**: ⏯ Ready for dictation | **Version**: Latest | **Platform**: macOS Primary
