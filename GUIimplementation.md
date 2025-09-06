# GUI Implementation Plan for Whisper Dictation

## 🎯 Objective
Implement a visual GUI overlay that shows real-time transcription during speech but pastes the final, accurate chunk-based transcription - combining the best of both worlds.

## 📊 Current State Analysis

### What We Have
1. **ui_components.py** - Complete GUI overlay with:
   - TranscriptionOverlay window (700px wide)
   - Audio visualization (60 frequency bars)
   - Real-time text display area
   - Recording status indicator
   - Auto-hide functionality

2. **Two Transcription Modes Available**:
   - **Real-time mode**: Less accurate, continuous updates (`enable_realtime_transcription=True`)
   - **Chunk mode**: More accurate final transcription (`recorder.text()`)

3. **Two Working Trigger Systems**:
   - **Double-Command**: Uses chunk mode only (accurate) ✅
   - **Jarvis Wake Word**: Currently using chunk mode (needs enhancement)

## 🏗️ Implementation Architecture

### Dual Transcription Strategy
```
User Speech → RealtimeSTT Engine
                ├─→ Real-time Transcription → GUI Display (continuous updates)
                └─→ Final Chunk Transcription → Clipboard Paste (accurate)
```

### Key Components to Modify

#### 1. **wake_word_wrapper.py** Changes
```python
class WakeWordRealtimeSTTWrapper:
    def __init__(self, ...):
        # Add UI manager
        self.ui_manager = None
        
        # Enable BOTH modes
        self.real_time_text = ""  # For GUI display
        self.final_text = ""      # For paste
        
    def _initialize_recorder(self):
        self.recorder = AudioToTextRecorder(
            # CHANGE: Enable real-time for GUI
            enable_realtime_transcription=True,  # Was False
            on_realtime_transcription_update=self._on_realtime_update,
            on_realtime_transcription_stabilized=self._on_stabilized_update,
            # Keep existing callbacks...
        )
    
    def _on_realtime_update(self, text):
        """Update GUI with real-time text"""
        self.real_time_text = text
        if self.ui_manager:
            self.ui_manager.update_transcription(text, is_final=False)
    
    def _on_stabilized_update(self, text):
        """Update GUI with stabilized segments"""
        if self.ui_manager:
            self.ui_manager.update_transcription(text, is_final=False)
    
    def transcribe(self):
        """Get final accurate transcription for paste"""
        # Show GUI
        if self.ui_manager:
            self.ui_manager.start_recording()
        
        # Get FINAL chunk transcription (accurate)
        final_text = self.recorder.text()
        
        # Update GUI with final text
        if self.ui_manager:
            self.ui_manager.update_transcription(final_text, is_final=True)
            self.ui_manager.stop_recording()
        
        # Paste the FINAL accurate text
        if final_text:
            self.type_text(final_text)
        
        return final_text
```

#### 2. **host_key_listener.py** Integration
```python
def run_wake_word_listener():
    from wake_word_wrapper import WakeWordRealtimeSTTWrapper
    from ui_components import UIManager
    
    # Create UI manager
    ui_manager = UIManager(None)  # No rumps app for wake word
    
    # Create wrapper with UI
    wrapper = WakeWordRealtimeSTTWrapper(
        model=CONFIG.get("model_name", "base"),
        language=CONFIG.get("language", "en"),
        wake_word="jarvis",
        sensitivity=1.0
    )
    
    # Connect UI to wrapper
    wrapper.ui_manager = ui_manager
    
    # Start continuous listening
    wrapper.continuous_listen()
```

#### 3. **Double-Command Enhancement** (Optional)
Add same GUI support to keyboard trigger for consistency:
```python
class RealtimeSTTWrapper:
    def transcribe_with_gui(self, ui_manager):
        ui_manager.start_recording()
        # ... existing transcription logic
        ui_manager.stop_recording()
```

## 📋 Implementation Steps

### Phase 1: Enable Real-time Mode ✅
1. ☐ Modify `wake_word_wrapper.py` to enable `enable_realtime_transcription=True`
2. ☐ Add real-time update callbacks (`on_realtime_transcription_update`)
3. ☐ Keep using `recorder.text()` for final paste

### Phase 2: Integrate UI Components
1. ☐ Import UIManager in `host_key_listener.py`
2. ☐ Create UIManager instance in wake word thread
3. ☐ Connect UIManager to WakeWordRealtimeSTTWrapper
4. ☐ Test GUI window appears during transcription

### Phase 3: Connect Real-time Updates
1. ☐ Implement `_on_realtime_update()` callback
2. ☐ Pass real-time text to `ui_manager.update_transcription()`
3. ☐ Show gray text for partial, white for final
4. ☐ Test real-time updates appear in GUI

### Phase 4: Audio Visualization
1. ☐ Add audio callback to RealtimeSTT
2. ☐ Pass audio chunks to `ui_manager.update_audio_levels()`
3. ☐ Test frequency bars animate during speech

### Phase 5: Polish & Testing
1. ☐ Auto-hide window after transcription
2. ☐ Position window appropriately
3. ☐ Test with various speech patterns
4. ☐ Verify final paste is accurate (not real-time)

## 🔍 Testing Checklist

### Functional Tests
- [ ] GUI appears when saying "Jarvis"
- [ ] Real-time text updates during speech
- [ ] Final pasted text is MORE accurate than real-time
- [ ] Audio bars animate with voice
- [ ] Window auto-hides after completion

### Quality Tests
- [ ] No lag in real-time updates
- [ ] Final transcription matches chunk mode quality
- [ ] GUI doesn't interfere with paste operation
- [ ] Memory/CPU usage acceptable

### Edge Cases
- [ ] Multiple rapid transcriptions
- [ ] Very long speech input
- [ ] Background noise handling
- [ ] System sleep/wake cycles

## 🎯 Success Criteria

1. **User Experience**:
   - See what's being transcribed in real-time
   - Get accurate final text pasted
   - Visual feedback during recording

2. **Technical**:
   - Real-time mode for display only
   - Chunk mode for final paste
   - No accuracy loss in final output

3. **Performance**:
   - < 100ms latency for real-time updates
   - No increase in final transcription time
   - Smooth 20+ FPS audio visualization

## 📈 Progress Tracking

- [x] Plan created
- [ ] Phase 1: Enable real-time mode
- [ ] Phase 2: Integrate UI components
- [ ] Phase 3: Connect real-time updates
- [ ] Phase 4: Audio visualization
- [ ] Phase 5: Polish & testing

## 🚀 Next Immediate Actions

1. **First**: Enable `enable_realtime_transcription=True` in wake_word_wrapper.py
2. **Second**: Add real-time callback handlers
3. **Third**: Import and initialize UIManager
4. **Test**: Verify GUI appears with "Jarvis" trigger