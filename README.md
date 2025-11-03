# 🎤 Whisper Dictation with AI Enhancement

**Voice-to-text system that transcribes your speech locally and enhances it with AI-powered grammar, punctuation, and capitalization.**

Perfect for:
- 📧 Drafting emails and documents hands-free
- 📝 Taking quick notes while working
- 💻 Dictating code comments or documentation
- ♿ Accessibility and assistive technology

## ✨ Key Features

- **⌨️ Keyboard Activation**: Double Right Cmd to start dictating instantly
- **🤖 AI Text Enhancement**: Automatic grammar, punctuation, and capitalization using local LLM (Qwen 2.5)
- **🔒 100% Offline**: No data leaves your machine - complete privacy
- **⚡ Fast**: 0.24s transcription + ~800ms enhancement = sub-second results
- **🌍 Multilingual**: Supports 99+ languages via Whisper models
- **📋 Auto-Paste**: Seamlessly inserts text wherever you're typing

> **Note**: Wake word activation ("Jarvis") is available in the codebase but currently disabled. See `src/services/keyboard_service.py` to enable.

## 🚀 Quick Start

### Prerequisites
```bash
# Install system dependencies
brew install portaudio llvm

# Install Ollama for AI text enhancement
brew install ollama

# Download the enhancement model (one-time, ~4.7GB)
ollama pull qwen2.5:7b-instruct
```

### Installation
```bash
git clone https://github.com/foges/whisper-dictation.git
cd whisper-dictation

# Using Poetry (recommended)
poetry install && poetry shell

# Or using pip
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Start Dictating
```bash
# Start the service with AI enhancement
./bin/run.sh

# Or run directly as a module:
python -m src.services.keyboard_service

# Then simply:
# Press Right Cmd twice + your text + Right Cmd once to stop
```

> **Note**: Wake word ("Jarvis") activation is currently disabled in the code. Only the double Right Command keyboard shortcut is active.

### Grant Permissions

**IMPORTANT**: macOS requires permissions for the specific Python executable in your virtual environment.

#### Step 1: Find Your Python Path
```bash
# After activating your environment, get the exact Python path:

# If using Poetry:
poetry shell
which python

# If using venv:
source venv/bin/activate
which python

# This will show something like:
# /Users/yourname/Library/Caches/pypoetry/virtualenvs/whisper-xyz/bin/python
# OR
# /path/to/whisper/venv/bin/python3
```

#### Step 2: Add Python to Accessibility
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **"+"** button at the bottom
3. Press **Cmd+Shift+G** to open "Go to folder" dialog
4. **Paste the exact Python path** from Step 1
5. Click "Open" and ensure the toggle is enabled

#### Step 3: Add Python to Microphone
1. Open **System Settings → Privacy & Security → Microphone**
2. Repeat the same process with the **same Python path**

> **Tip**: If the service doesn't work, verify the correct Python binary is listed in Privacy settings. It should match the output of `which python` when your environment is activated.

## 🤖 AI Text Enhancement

Your transcribed speech is automatically enhanced with proper grammar and punctuation:

**How it works:**
- Local LLM (Qwen 2.5 7B) running via Ollama
- Average processing time: ~800ms
- Completely private - no cloud APIs
- Automatic fallback if LLM unavailable

**Example transformations:**
```
Raw:        "hey can you send me that document we discussed yesterday"
Enhanced:   "Hey, can you send me that document we discussed yesterday?"

Raw:        "im working on the authentication module it should be done by friday"
Enhanced:   "I'm working on the authentication module. It should be done by Friday."
```

**Configuration** (in `src/config.py`):
```python
"text_enhancement_settings": {
    "engine": "ollama",
    "ollama_model": "qwen2.5:7b-instruct",
    "max_latency_ms": 2000,           # 2s timeout
    "min_words_for_enhancement": 3,   # Skip 1-2 word commands
}
```

## 📋 Usage Options

### Command Line Options

```bash
python whisper_dictation.py [OPTIONS]

# Common options:
-m, --model_name    # Whisper model: tiny, base (default), small, medium, large
-l, --language      # Language code: en, es, fr, de, etc. (99+ supported)
-k, --key           # Custom hotkey combination
--k_double_cmd      # Use double Right Cmd trigger
```

### Model Selection

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `tiny` | 39MB | Fastest | Quick notes, older hardware |
| `base` | 74MB | Fast | **Recommended for most users** |
| `small` | 244MB | Medium | Better accuracy |
| `large` | 1.5GB | Slowest | Maximum accuracy |

### Keyboard Controls

| Action | Shortcut |
|--------|----------|
| Start recording | Double Right Cmd (press twice quickly) |
| Stop recording | Right Cmd (single press) |

> **Note**: Wake word activation is currently disabled. Only keyboard shortcuts are active.

## 🔧 Service Management (Auto-Start)

```bash
# Install service to start on login
cp com.whisper.service.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.whisper.service.plist

# Control service
./manage_whisper.py start|stop|restart|status

# Logs
tail -f /var/log/whisper/whisper.log
```

## 🐳 Docker Deployment

For containerized deployment with health monitoring, see [DOCKER.md](docs/DOCKER.md).

## ☁️ AWS Integration

Optional AWS Transcribe streaming integration available. See [AWS_INTEGRATION.md](docs/README_AWS_INTEGRATION.md).

## ⚙️ Configuration

Main config file: `src/config.py`

Key settings:
- **Whisper model**: Change `model_name` in config
- **Text enhancement**: Configure LLM model and timeout in `text_enhancement_settings`
- **Wake word**: Enable/disable in `wake_word_settings`
- **Languages**: Supports 99+ languages via `language` setting

## 🔍 Troubleshooting

**Recording not starting:**
- Grant Accessibility & Microphone permissions (System Settings → Privacy & Security)
- Check logs: `tail -f /var/log/whisper/whisper.log`

**Poor transcription quality:**
- Use larger model: `-m medium` or `-m large`
- Specify language: `-l en`
- Reduce background noise

**Text enhancement slow/failing:**
- Ensure Ollama is running: `ollama serve`
- Check model is downloaded: `ollama list`
- Falls back to rules-based enhancement if timeout

**Service issues:**
```bash
./manage_whisper.py status
launchctl unload ~/Library/LaunchAgents/com.whisper.service.plist
launchctl load ~/Library/LaunchAgents/com.whisper.service.plist
```

## 🔧 Development

### Architecture

**Core Components:**
- `src/backends/` - RealtimeSTT wrapper and transcription interface
- `src/services/` - Wake word detection, keyboard handling, text enhancement
- `src/utils/` - Clipboard, audio monitoring, event system
- `src/config.py` - Central configuration

**Key Technologies:**
- OpenAI Whisper for speech recognition
- RealtimeSTT for real-time transcription
- Ollama + Qwen 2.5 for text enhancement
- Porcupine for wake word detection

### Recent Improvements

- ✅ AI text enhancement with local LLM (~800ms avg)
- ✅ Whisper vocabulary grounding for better domain term recognition
- ✅ Recording popup with waveform visualization
- ✅ Unified transcription pattern with backdate trimming
- ✅ Unlimited recording time (removed 30s limit)

### Contributing

Fork, create feature branch, test thoroughly, submit PR. See project structure in `CLAUDE.md`.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the Whisper ASR model
- Contributors and community feedback
- macOS accessibility framework developers

---

**Status**: ⏯ Ready for dictation | **Version**: Latest | **Platform**: macOS Primary
