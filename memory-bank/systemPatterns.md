# System Patterns

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
2025-06-02 00:09:38 - Initial Memory Bank creation and system patterns documentation

## Coding Patterns

### Service Architecture Pattern
* **Pattern**: Robust service wrapper with process monitoring and auto-restart
* **Implementation**: `whisper_service.py` monitors main process health and provides immediate restart on crashes
* **Benefits**: Ensures high availability and automatic recovery from failures

### Resource Management Pattern
* **Pattern**: Context managers and proper cleanup for system resources
* **Implementation**: Enhanced PyAudio stream cleanup, multiprocessing resource management
* **Benefits**: Prevents resource leaks and improves system stability

### Signal Handling Pattern
* **Pattern**: Graceful shutdown with proper signal handling
* **Implementation**: SIGINT and SIGTERM handlers for orderly resource cleanup
* **Benefits**: Prevents segmentation faults and ensures clean termination

## Architectural Patterns

### Offline-First Architecture
* **Pattern**: Complete local processing with no external dependencies
* **Implementation**: Local Whisper model execution, no cloud API calls
* **Benefits**: Privacy preservation, no data sharing, works without internet

### Service Management Pattern
* **Pattern**: macOS LaunchAgent integration for system startup
* **Implementation**: `com.whisper.service.plist` for automatic service startup
* **Benefits**: Seamless user experience with background operation

### Modular Component Design
* **Pattern**: Separation of concerns across multiple specialized components
* **Components**: 
  - Core dictation engine (`whisper_dictation.py`)
  - Service wrapper (`whisper_service.py`)
  - Management interface (`manage_whisper.py`)
* **Benefits**: Maintainable codebase with clear responsibilities

## Testing Patterns

### Extended Run Testing
* **Pattern**: Long-duration stability testing with multiple recording sessions
* **Implementation**: Continuous operation testing with start/stop cycles
* **Benefits**: Validates resource cleanup and prevents memory leaks

### Process Lifecycle Testing
* **Pattern**: Testing graceful shutdown and restart scenarios
* **Implementation**: Signal handling validation and cleanup verification
* **Benefits**: Ensures robust operation under various termination conditions
## Architectural Patterns

**2025-06-02 01:19:02** - Strategy Pattern Implementation for Transcription Services
- Implemented Strategy pattern with TranscriptionService abstract base class
- Concrete implementations: WhisperTranscriptionService and AWSTranscriptionService
- Enables runtime selection of transcription backend via command line flags
- Maintains consistent interface while allowing different implementation strategies
- Supports easy extension for additional transcription services (Google, Azure, etc.)

**2025-06-02 01:19:02** - Abstract Factory Pattern for Service Instantiation
- Main application uses factory-like logic to instantiate appropriate transcription service
- Conditional instantiation based on command line flags (--use_aws_transcribe)
- Prevents unnecessary resource allocation (no Whisper model loading when using AWS)
- Clean separation between service selection logic and service implementation

**2025-06-02 01:19:02** - Adapter Pattern for API Integration
- AWSTranscriptionService adapts streaming AWS Transcribe API to batch-processing interface
- Maintains consistent user experience across different underlying API paradigms
- Handles complexity of streaming API while presenting simple transcribe() method
- Language code mapping between Whisper and AWS Transcribe formats

## Coding Patterns

**2025-06-02 01:19:02** - Abstract Base Class with Template Method
- TranscriptionService defines contract with transcribe() and cleanup() methods
- Concrete classes implement specific transcription logic while maintaining interface
- Template method pattern ensures consistent lifecycle management
- Error handling standardized across all implementations

**2025-06-02 01:19:02** - Resource Management Pattern
- Conditional resource loading based on runtime configuration
- Proper cleanup methods implemented for both local and cloud resources
- Memory-efficient approach preventing unnecessary model loading
- Graceful error handling for missing dependencies or credentials

**2025-06-02 01:19:02** - Configuration-Driven Architecture
- Command line arguments drive service selection and configuration
- Feature flag pattern for enabling/disabling AWS Transcribe functionality
- Extensible configuration system supporting additional parameters (region, etc.)
- Backward compatibility maintained with existing Whisper-only usage

## Testing Patterns

**2025-06-02 01:19:02** - Interface-Based Testing Strategy
- Abstract TranscriptionService interface enables easy mocking for unit tests
- Concrete implementations can be tested independently
- Integration tests can verify both local and cloud transcription paths
- Error scenarios testable through dependency injection and mocking