#!/usr/bin/env python3
"""
Streaming Text Overlay - macOS-style dictation notification

Provides a sleek, floating overlay window for real-time transcription display
that mimics macOS native dictation UI with smooth text streaming updates.
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from overlay import Window
from typing import Optional, Callable


class StreamingOverlay:
    """
    A floating, semi-transparent overlay window for streaming text display.
    
    Features:
    - Transparent, draggable window
    - Real-time text updates via StringVar
    - macOS-style appearance (dark background, rounded corners)
    - Auto-positioning in top-right corner
    - Fade-in/fade-out animations
    - Auto-hide after completion
    """
    
    def __init__(self):
        self.window: Optional[Window] = None
        self.text_var: Optional[tk.StringVar] = None
        self.label: Optional[tk.Label] = None
        self.is_visible = False
        self.auto_hide_timer: Optional[threading.Timer] = None
        self.fade_animation_active = False
        
        # Styling configuration
        self.config = {
            'bg_color': '#1C1C1E',           # Dark background like macOS
            'text_color': '#FFFFFF',         # White text
            'partial_text_color': '#CCCCCC', # Gray for partial transcription
            'font_family': 'SF Pro Text',    # macOS system font
            'font_size': 14,
            'padding_x': 20,
            'padding_y': 12,
            'corner_radius': 12,             # Rounded corners
            'window_alpha': 0.92,            # Semi-transparent
            'window_width': 400,
            'window_height': 80,
            'auto_hide_delay': 3.0,          # Seconds to auto-hide after final text
        }
    
    def create_window(self):
        """Create and configure the floating overlay window."""
        if self.window is not None:
            return
            
        # Create overlay window with transparency
        self.window = Window(
            transparent=True,
            alpha=self.config['window_alpha']
        )
        
        # Configure window properties
        root = self.window.root
        root.overrideredirect(True)  # Remove window decorations
        root.attributes('-topmost', True)  # Always on top
        root.attributes('-alpha', self.config['window_alpha'])
        root.configure(bg=self.config['bg_color'])
        
        # Position in top-right corner of screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_pos = screen_width - self.config['window_width'] - 50  # 50px margin from right
        y_pos = 50  # 50px margin from top
        
        root.geometry(f"{self.config['window_width']}x{self.config['window_height']}+{x_pos}+{y_pos}")
        
        # Create main frame with rounded appearance
        self.main_frame = tk.Frame(
            root,
            bg=self.config['bg_color'],
            padx=self.config['padding_x'],
            pady=self.config['padding_y']
        )
        self.main_frame.pack(fill='both', expand=True)
        
        # Create StringVar for real-time text updates
        self.text_var = tk.StringVar(value="Listening...")
        
        # Create text label
        self.label = tk.Label(
            self.main_frame,
            textvariable=self.text_var,
            bg=self.config['bg_color'],
            fg=self.config['text_color'],
            font=(self.config['font_family'], self.config['font_size']),
            wraplength=self.config['window_width'] - (self.config['padding_x'] * 2),
            justify='left',
            anchor='w'
        )
        self.label.pack(fill='both', expand=True)
        
        # Add subtle shadow effect with border frame
        shadow_frame = tk.Frame(
            root,
            bg='#000000',
            highlightthickness=1,
            highlightcolor='#333333'
        )
        shadow_frame.place(x=2, y=2, width=self.config['window_width'], height=self.config['window_height'])
        shadow_frame.lower()  # Put shadow behind main frame
        
        self.is_visible = True
    
    def show(self, initial_text: str = "Listening..."):
        """Show the overlay window with initial text."""
        if not self.is_visible:
            self.create_window()
        
        self.update_text(initial_text, is_final=False)
        self._fade_in()
    
    def hide(self):
        """Hide the overlay window with fade-out animation."""
        if self.is_visible:
            self._fade_out()
    
    def update_text(self, text: str, is_final: bool = False):
        """
        Update the displayed text in real-time.
        
        Args:
            text: The text to display
            is_final: True if this is final transcription, False for partial
        """
        if not self.is_visible or self.text_var is None:
            return
        
        # Update text content
        self.text_var.set(text)
        
        # Change color based on text type
        if self.label:
            color = self.config['text_color'] if is_final else self.config['partial_text_color']
            self.label.configure(fg=color)
        
        # Auto-resize window based on text length
        self._auto_resize_window()
        
        # If this is final text, start auto-hide timer
        if is_final:
            self._schedule_auto_hide()
    
    def _auto_resize_window(self):
        """Automatically resize window based on text content."""
        if not self.label or not self.window:
            return
        
        # Force update to get accurate measurements
        self.window.root.update_idletasks()
        
        # Calculate required height
        required_width = self.label.winfo_reqwidth() + (self.config['padding_x'] * 2)
        required_height = self.label.winfo_reqheight() + (self.config['padding_y'] * 2)
        
        # Apply constraints
        min_width = 200
        max_width = 600
        min_height = 60
        max_height = 200
        
        new_width = max(min_width, min(max_width, required_width))
        new_height = max(min_height, min(max_height, required_height))
        
        # Only resize if significantly different
        current_width = self.window.root.winfo_width()
        current_height = self.window.root.winfo_height()
        
        if abs(new_width - current_width) > 20 or abs(new_height - current_height) > 10:
            # Recalculate position to maintain top-right corner
            screen_width = self.window.root.winfo_screenwidth()
            x_pos = screen_width - new_width - 50
            y_pos = 50
            
            self.window.root.geometry(f"{new_width}x{new_height}+{x_pos}+{y_pos}")
            self.config['window_width'] = new_width
            self.config['window_height'] = new_height
    
    def _fade_in(self):
        """Animate window fade-in."""
        if self.fade_animation_active or not self.window:
            return
        
        self.fade_animation_active = True
        target_alpha = self.config['window_alpha']
        steps = 10
        step_size = target_alpha / steps
        
        def animate_step(current_alpha, step):
            if step >= steps or not self.window:
                self.fade_animation_active = False
                return
            
            new_alpha = current_alpha + step_size
            self.window.root.attributes('-alpha', new_alpha)
            
            # Schedule next step
            self.window.root.after(30, lambda: animate_step(new_alpha, step + 1))
        
        # Start with low alpha
        self.window.root.attributes('-alpha', 0.1)
        animate_step(0.1, 0)
    
    def _fade_out(self):
        """Animate window fade-out and destroy."""
        if self.fade_animation_active or not self.window:
            return
        
        self.fade_animation_active = True
        current_alpha = self.window.root.attributes('-alpha')
        steps = 8
        step_size = current_alpha / steps
        
        def animate_step(alpha, step):
            if step >= steps or not self.window:
                self._destroy_window()
                return
            
            new_alpha = alpha - step_size
            if new_alpha > 0:
                self.window.root.attributes('-alpha', new_alpha)
                self.window.root.after(40, lambda: animate_step(new_alpha, step + 1))
            else:
                self._destroy_window()
        
        animate_step(current_alpha, 0)
    
    def _schedule_auto_hide(self):
        """Schedule automatic hiding after final text is displayed."""
        # Cancel existing timer
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
        
        # Schedule new timer
        self.auto_hide_timer = threading.Timer(
            self.config['auto_hide_delay'], 
            self.hide
        )
        self.auto_hide_timer.start()
    
    def _destroy_window(self):
        """Clean up and destroy the window."""
        self.fade_animation_active = False
        
        # Cancel auto-hide timer
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            self.auto_hide_timer = None
        
        # Destroy window
        if self.window:
            try:
                self.window.root.destroy()
            except:
                pass  # Window might already be destroyed
            self.window = None
        
        # Reset state
        self.text_var = None
        self.label = None
        self.is_visible = False
    
    def cleanup(self):
        """Cleanup resources."""
        self._destroy_window()


class StreamingOverlayManager:
    """
    Manager class for controlling the streaming overlay.
    Provides a simple interface for transcription callbacks.
    """
    
    def __init__(self):
        self.overlay = StreamingOverlay()
        self.is_recording = False
    
    def start_recording(self):
        """Start recording and show overlay."""
        if not self.is_recording:
            self.is_recording = True
            self.overlay.show("Listening...")
    
    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription text in real-time."""
        if self.is_recording:
            self.overlay.update_text(text, is_final=is_final)
            
            if is_final:
                self.is_recording = False
    
    def stop_recording(self):
        """Stop recording and hide overlay."""
        if self.is_recording:
            self.is_recording = False
            self.overlay.hide()
    
    def cleanup(self):
        """Cleanup resources."""
        self.overlay.cleanup()


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    def test_streaming_overlay():
        """Test function to demonstrate streaming overlay functionality."""
        manager = StreamingOverlayManager()
        
        try:
            # Show initial recording state
            manager.start_recording()
            
            # Simulate streaming transcription updates
            test_phrases = [
                "Hello",
                "Hello world",
                "Hello world this",
                "Hello world this is",
                "Hello world this is a",
                "Hello world this is a test",
                "Hello world this is a test of",
                "Hello world this is a test of the",
                "Hello world this is a test of the streaming",
                "Hello world this is a test of the streaming overlay",
                "Hello world this is a test of the streaming overlay system."
            ]
            
            # Stream partial updates
            for i, phrase in enumerate(test_phrases):
                is_final = (i == len(test_phrases) - 1)
                manager.update_transcription(phrase, is_final=is_final)
                time.sleep(0.3)  # Simulate real-time updates
            
            # Keep window open for a bit to see auto-hide
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        finally:
            manager.cleanup()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_streaming_overlay()
    else:
        print("StreamingOverlay module loaded successfully!")
        print("Run with 'test' argument to see demo: python streaming_overlay.py test")