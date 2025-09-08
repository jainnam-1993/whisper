"""
Shared event system for coordinating recording state between services.
Allows keyboard service to track recording events.
"""

import threading
from typing import Callable, Dict, List
from enum import Enum


class RecordingEvent(Enum):
    """Types of recording events that can be emitted"""
    MANUAL_STOP_REQUESTED = "manual_stop_requested"
    MANUAL_RECORDING_STARTED = "manual_recording_started"
    MANUAL_RECORDING_STOPPED = "manual_recording_stopped"


class RecordingEventManager:
    """
    Thread-safe event manager for recording state coordination.
    
    Allows services to:
    - Subscribe to recording events
    - Emit recording events  
    - Query current recording state
    """
    
    def __init__(self):
        self._subscribers: Dict[RecordingEvent, List[Callable]] = {}
        self._lock = threading.Lock()
        self._manual_recording = False
    
    def subscribe(self, event: RecordingEvent, callback: Callable) -> None:
        """Subscribe to a recording event"""
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            self._subscribers[event].append(callback)
    
    def emit(self, event: RecordingEvent, **kwargs) -> None:
        """Emit a recording event to all subscribers"""
        with self._lock:
            # Update internal state
            if event == RecordingEvent.MANUAL_RECORDING_STARTED:
                self._manual_recording = True
            elif event == RecordingEvent.MANUAL_RECORDING_STOPPED:
                self._manual_recording = False
            
            # Notify subscribers
            if event in self._subscribers:
                for callback in self._subscribers[event]:
                    try:
                        callback(**kwargs)
                    except Exception as e:
                        print(f"Error in event callback for {event}: {e}")
    
    
    def is_manual_recording(self) -> bool:
        """Check if manual recording is currently active"""
        with self._lock:
            return self._manual_recording
    
    def is_any_recording(self) -> bool:
        """Check if any recording is currently active"""
        with self._lock:
            return self._manual_recording