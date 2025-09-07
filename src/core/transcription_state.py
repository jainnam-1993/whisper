#!/usr/bin/env python3
"""
Unified Transcription State Management
Provides thread-safe state management for transcription text across all services
"""

import threading
from typing import Optional
from dataclasses import dataclass


@dataclass
class TranscriptionState:
    """
    Unified transcription state with clear semantics
    
    Attributes:
        current_text: The current transcription text (partial or final)
        is_final: Whether this text is finalized (true) or still being processed (false)
        is_stable: Whether this text has been stabilized (for real-time updates)
    """
    current_text: str = ""
    is_final: bool = False
    is_stable: bool = False
    

class ThreadSafeTranscriptionState:
    """
    Thread-safe wrapper for transcription state management
    
    This replaces the competing variables:
    - partial_text -> current_text with is_final=False
    - real_time_text -> current_text with is_final=False, is_stable=False  
    - final_text -> current_text with is_final=True
    - last_complete_text -> current_text with is_final=False, is_stable=True
    """
    
    def __init__(self):
        self._state = TranscriptionState()
        self._lock = threading.RLock()
    
    def update_text(self, text: str, is_final: bool = False, is_stable: bool = False) -> None:
        """
        Update transcription text with thread safety
        
        Args:
            text: The transcription text
            is_final: Whether this is the final transcription result
            is_stable: Whether this text has been stabilized (for real-time)
        """
        with self._lock:
            self._state.current_text = text
            self._state.is_final = is_final
            self._state.is_stable = is_stable
    
    def get_current_text(self) -> str:
        """Get the current transcription text"""
        with self._lock:
            return self._state.current_text
    
    def get_state(self) -> TranscriptionState:
        """Get a copy of the current state"""
        with self._lock:
            return TranscriptionState(
                current_text=self._state.current_text,
                is_final=self._state.is_final,
                is_stable=self._state.is_stable
            )
    
    def is_final(self) -> bool:
        """Check if current text is final"""
        with self._lock:
            return self._state.is_final
    
    def is_stable(self) -> bool:
        """Check if current text is stable"""
        with self._lock:
            return self._state.is_stable
    
    def has_text(self) -> bool:
        """Check if there is any text available"""
        with self._lock:
            return bool(self._state.current_text and self._state.current_text.strip())
    
    def clear(self) -> None:
        """Clear all transcription state"""
        with self._lock:
            self._state.current_text = ""
            self._state.is_final = False
            self._state.is_stable = False
    
    def get_best_text(self) -> Optional[str]:
        """
        Get the best available text with fallback logic
        
        Priority:
        1. Final text (highest priority)
        2. Stable text (medium priority) 
        3. Current text (lowest priority)
        
        Returns:
            The best available text or None if no text
        """
        with self._lock:
            if self._state.current_text and self._state.current_text.strip():
                return self._state.current_text.strip()
            return None


# Legacy compatibility functions for gradual migration
def create_transcription_state() -> ThreadSafeTranscriptionState:
    """Factory function for creating transcription state instances"""
    return ThreadSafeTranscriptionState()