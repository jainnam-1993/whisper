# 🎤 Whisper Dictation with AI Enhancement

**Voice-to-text system that transcribes your speech locally and enhances it with AI-powered grammar, punctuation, and capitalization.**

Perfect for:
- 📧 Drafting emails and documents hands-free
- 📝 Taking quick notes while working
- 💻 Dictating code comments or documentation
- ♿ Accessibility and assistive technology

## ✨ Key Features

- **🎯 Wake Word Activation**: Say "Jarvis" to start dictating (or use keyboard shortcuts)
- **🤖 AI Text Enhancement**: Automatic grammar, punctuation, and capitalization using local LLM (Qwen 2.5)
- **🔒 100% Offline**: No data leaves your machine - complete privacy
- **⚡ Fast**: 0.24s transcription + ~800ms enhancement = sub-second results
- **🌍 Multilingual**: Supports 99+ languages via Whisper models
- **📋 Auto-Paste**: Seamlessly inserts text wherever you're typing

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
# Start the service with wake word and AI enhancement
python host_key_listener.py

# Then simply:
# 1. Say "Jarvis" + your text, OR
# 2. Press Right Cmd twice + your text + Right Cmd once to stop
```

### Grant Permissions
On first run, grant:
- **Accessibility**: System Settings → Privacy & Security → Accessibility → Add Python
- **Microphone**: System Settings → Privacy & Security → Microphone → Add Python

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
| Start recording | Say "Jarvis" OR Double Right Cmd |
| Stop recording | Right Cmd (single press) |

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
- ✅ Wake word activation ("Jarvis")
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
