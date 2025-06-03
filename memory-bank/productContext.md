# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.

2025-06-02 00:08:09 - Initial Memory Bank creation for Whisper Dictation project

## Project Goal

The Whisper Dictation project is a multilingual dictation application based on OpenAI's Whisper ASR model that provides accurate and efficient speech-to-text conversion. The system runs entirely offline to ensure privacy and data security, operating as a background service triggered by keyboard shortcuts.

## Key Features

* **Offline Operation**: Completely local processing with no data sharing to external services
* **Multilingual Support**: Supports multiple languages with configurable language codes
* **Multiple Whisper Models**: Choice between tiny, base, small, medium, and large models
* **Keyboard Shortcuts**: Configurable hotkey combinations for activation
* **Background Service**: Runs as a system service with auto-restart capabilities
* **macOS Integration**: Designed specifically for macOS with accessibility permissions
* **Resource Management**: Enhanced cleanup and stability improvements
* **Service Architecture**: Robust service wrapper with crash recovery

## Overall Architecture

The system consists of several key components:

1. **Core Dictation Engine** (`whisper_dictation.py`) - Main application logic
2. **Service Wrapper** (`whisper_service.py`) - Process monitoring and crash recovery
3. **Management Interface** (`manage_whisper.py`) - Control commands for service lifecycle
4. **Auto-startup Integration** (`com.whisper.service.plist`) - macOS LaunchAgent configuration
5. **Audio Processing** - PyAudio integration for microphone input
6. **Transcription Pipeline** - OpenAI Whisper model integration

The architecture emphasizes stability, resource management, and seamless user experience while maintaining complete offline operation.
# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.

## Project Goal

**Enhanced Whisper Dictation Application with Dual Transcription Backend Support**

Transform the existing single-purpose Whisper dictation application into a flexible, multi-backend transcription system that supports both local Whisper processing and cloud-based AWS Transcribe services. The system maintains identical user experience regardless of backend choice while providing users the flexibility to choose between offline privacy (local Whisper) and cloud accuracy/speed (AWS Transcribe).

## Key Features

**Core Functionality:**
- Double command key press activation for recording start/stop (maintained from original)
- Real-time audio recording with visual feedback
- Automatic transcription processing with configurable backends
- Text output integration with system clipboard and applications

**Dual Backend Architecture:**
- **Local Whisper Backend**: Offline processing using local Whisper models for privacy and independence
- **AWS Transcribe Backend**: Cloud-based processing using AWS Transcribe streaming API for enhanced accuracy
- Command-line flag system for backend selection (`--use_aws_transcribe`)
- Conditional resource loading preventing unnecessary local model loading when using cloud services

**Advanced Features:**
- Multi-language support with automatic language code mapping between backends
- Comprehensive error handling for network connectivity and credential issues
- Resource-efficient architecture with smart memory management
- Extensible design supporting future transcription service integrations

## Overall Architecture

**Abstract Service Layer:**
- `TranscriptionService` abstract base class defining common interface
- Strategy pattern implementation enabling runtime backend selection
- Consistent API contract across all transcription implementations

**Concrete Implementations:**
- `WhisperTranscriptionService`: Wraps existing local Whisper functionality
- `AWSTranscriptionService`: Implements AWS Transcribe streaming integration with batch-processing user experience

**Application Layer:**
- `Recorder` class handles audio capture and user interaction
- Main application orchestrates service selection and lifecycle management
- Command-line interface provides user control over backend selection and configuration

**Key Architectural Decisions:**
- Maintained backward compatibility with existing Whisper-only usage
- Implemented streaming-to-batch adapter pattern for consistent user experience
- Used conditional dependency loading for optional AWS functionality
- Applied resource management patterns preventing unnecessary model loading

**Integration Points:**
- macOS system integration for keyboard shortcuts and audio capture
- AWS SDK integration for cloud transcription services
- Cross-platform audio processing and text output handling

2025-06-02 01:19:26 - Major architectural evolution from single-purpose Whisper application to dual-backend transcription system with Strategy pattern implementation and cloud service integration.