# 🎤 RealtimeSTT Whisper Voice Recognition System

## Project Overview
Voice-to-text system using RealtimeSTT with Whisper backend, supporting both wake word ("Jarvis") and manual double-command activation.

## Architecture Summary

### Core Components
1. **RealtimeSTT Backend** (`src/backends/realtimestt_backend.py`)
   - Manages the actual Whisper recorder instance
   - Handles start/stop/text operations
   - Uses `recorder.stop()` + `recorder.text()` pattern (NOT `abort()`)

2. **Keyboard Service** (`src/services/keyboard_service.py`)
   - Implements `DoubleCommandKeyListener` class
   - Handles Right Command key detection
   - Manages double-click logic for manual recording

3. **Wake Word Service** (`src/services/wake_word_service.py`)
   - Listens for "Jarvis" wake word
   - Handles manual stop via Right Command during wake word recording
   - Manages clipboard copy/paste operations

## Current Issues & Root Causes

### 🐛 Issue 1: Double Command Not Working
**Location**: `src/services/keyboard_service.py:172`
```python
self.last_press_time = 0  # Initial value causes huge time_diff
```
**Problem**: First press calculates `time_diff = current_time - 0`, resulting in ~1757286762 seconds
**Solution**: Initialize to `-999` or check for first press explicitly

### 🐛 Issue 2: Double Pasting in Wake Word
**Locations**: 
- `src/services/wake_word_service.py:368` - Manual stop handler pastes
- `src/services/wake_word_service.py:393` - `_process_final_text()` pastes again

**Problem**: Two separate code paths both call `clipboard.copy_and_paste_text()`
**Solution**: Manual stop should set a flag to skip duplicate processing

## Unified Transcription Pattern
**CRITICAL**: Always use this pattern for all transcription paths:
```python
trim_duration = config.get('min_length_of_recording', 0.3)
recorder.stop(
    backdate_stop_seconds=trim_duration,
    backdate_resume_seconds=trim_duration
)
text = recorder.text()
```

## Key Configuration
```python
CONFIG = {
    "wake_word_settings": {
        "min_length_of_recording": 0.3,  # Backdate trim duration
    },
    "keyboard_settings": {
        "min_length_of_recording": 0.3,  # Same for consistency
    }
}
```

## Important Code References

### Double Command Detection Logic
`src/services/keyboard_service.py:174-209` - `on_key_press()` method
- Lines 185-189: Manual stop during recording
- Lines 191-196: Double-click detection (BROKEN)
- Lines 198-201: Wake word manual stop

### Wake Word Manual Stop Handler  
`src/services/wake_word_service.py:352-380` - `_on_manual_stop_requested()`
- Line 360: Unified stop with backdate
- Line 368: First paste (correct)
- Line 377: Sets `manual_stop_requested = True`

### Final Text Processing
`src/services/wake_word_service.py:385-400` - `_process_final_text()`
- Line 393: Second paste (DUPLICATE - should check flag)

## Performance Notes
- Direct method calls (`stop()` + `text()`) are faster than event-driven callbacks
- `abort()` is for teardown/cancel, NOT for getting transcriptions
- `backdate_stop_seconds` removes wake word audio pollution

## Testing Checklist
**Note**: User will test manually - ask for confirmation before testing
- [ ] Double Right Command starts recording
- [ ] Single Right Command stops manual recording  
- [ ] Wake word "Jarvis" activates
- [ ] Right Command during wake word stops and pastes once
- [ ] No duplicate pasting in any workflow
- [ ] Both workflows have same transcription speed

## Fix Implementation Plan
1. Fix `last_press_time` initialization
2. Add `skip_final_processing` flag to prevent double paste
3. Verify `RealtimeSTTCommunicator` has required methods
4. Test both workflows end-to-end