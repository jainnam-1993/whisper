"""
Unified configuration for Whisper voice recognition system.
Shared across keyboard service, wake word service, and all backends.
"""

# ============================================================================
# BACKEND SELECTION
# ============================================================================
# Choose transcription backend:
# - "realtimestt": Uses RealtimeSTT with faster-whisper (patched to whisper.cpp)
# - "whisper.cpp": Direct whisper.cpp integration (experimental)
# ============================================================================

BACKEND = "realtimestt"  # Default: RealtimeSTT with whisper.cpp patch

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
# Model name for transcription
# - "medium": Best balance of speed/accuracy (recommended)
# - "medium-q5_0": Quantized model (3x less memory, slightly faster)
# - "small": Faster but less accurate
# - "large-v3": Most accurate but slower
# ============================================================================

MODEL_NAME = "large-v3"  # Used by both backends

# ============================================================================
# SHARED SETTINGS
# ============================================================================

CONFIG = {
    "model_name": MODEL_NAME,
    "language": "en",

    # ========================================================================
    # TEXT ENHANCEMENT SETTINGS
    # ========================================================================
    # Post-processing for transcribed text (capitalization, punctuation, grammar)
    # ========================================================================
    "text_enhancement_settings": {
        "engine": "ollama",                    # Enhancement engine: "ollama", "rules", or "disabled"
        "ollama_model": "qwen2.5:7b-instruct", # Qwen 2.5 7B Instruct (Apache 2.0, GPU-accelerated)
        "ollama_url": "http://localhost:11434", # Ollama API endpoint
        "max_latency_ms": 5000,                # Maximum acceptable latency for enhancement (5 seconds allows multi-paragraph text)
        "min_words_for_enhancement": 3,        # Skip enhancement for very short text (1-2 words)
    },

    # ========================================================================
    # KEYBOARD (Double Command) SETTINGS
    # ========================================================================
    # Manual recording triggered by double Right Command press
    # ========================================================================
    "keyboard_settings": {
        "enable_realtime": False,           # No real-time transcription during recording
        "pre_buffer_duration": 3.0,         # Seconds of audio to buffer before VAD trigger
        "vad_sensitivity": 0.3,             # Voice activity detection sensitivity (0.0-1.0)
        "post_speech_silence_duration": None,  # None = manual stop only (press Right Command to stop)
        "webrtc_sensitivity": 2,            # Alternative VAD method sensitivity (0-3)
        "min_length_of_recording": 0.0,     # Minimum recording length in seconds
        "min_gap_between_recordings": 0.0,  # Minimum gap between recordings in seconds
    },

    # ========================================================================
    # WAKE WORD SETTINGS
    # ========================================================================
    # Automatic recording triggered by saying "Jarvis"
    # ========================================================================
    "wake_word_settings": {
        "wake_words": "jarvis",                    # Wake word to activate recording
        "wake_words_sensitivity": 0.5,             # Wake word detection sensitivity (0.0-1.0)
        "wake_word_timeout": 5.0,                  # Seconds to wait for speech after wake word
        "wake_word_activation_delay": 0.0,         # Delay before starting recording after wake word
        "min_length_of_recording": 0.3,            # Minimum recording length (also backdate trim duration)
        "min_gap_between_recordings": 0.0,         # Minimum gap between recordings
        "enable_realtime": False,                  # No real-time transcription during recording
        "pre_buffer_duration": 1.0,                # Seconds of audio to buffer before wake word
        "vad_sensitivity": 0.3,                    # Voice activity detection sensitivity
        "post_speech_silence_duration": 0.7,       # Seconds of silence before auto-stop
        "webrtc_sensitivity": 2,                   # Alternative VAD method sensitivity
    }
}


# ============================================================================
# PICOVOICE API KEY (for wake word detection)
# ============================================================================
# Used by pvporcupine library for wake word "Jarvis" detection
# ============================================================================

PICOVOICE_ACCESS_KEY = "lk++IHEpUel5qLDl6dc4e2qR12RqlKoMNzILpflCnLYVuTba4t3v0w=="
