"""
Modern UI components for Whisper Dictation with real-time transcription display
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import math
from typing import Optional, Callable, List
import queue
import numpy as np


class TranscriptionOverlay:
    """
    A floating overlay window that displays real-time transcription with modern UI
    """
    
    def __init__(self):
        self.window = None
        self.text_var = None
        self.is_recording = False
        self.animation_thread = None
        self.update_queue = queue.Queue()
        self._stop_animation = threading.Event()
        self.audio_levels = []
        self.audio_visualizer_bars = []
        self.current_text = ""
        self.window_height = 180  # Increased for audio visualizer
        
    def create_window(self):
        """Create the floating overlay window"""
        # Clean up existing window if any
        if self.window is not None:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None
            
        self.window = tk.Tk()
        self.window.title("")
        
        # Make window floating and transparent
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.9)  # Slightly more transparent
        
        # Remove window decorations for cleaner look
        self.window.overrideredirect(True)
        
        # Configure window styling - darker background
        self.window.configure(bg='#1a1a1a')
        
        # Position at top-right corner of screen (like macOS notifications)
        screen_width = self.window.winfo_screenwidth()
        self.window_width = 400  # Narrower, more compact
        self.window_height = 80  # Much shorter, just for text
        x = screen_width - self.window_width - 20  # 20px from right edge
        y = 40  # 40px from top
        
        self.window.geometry(f'{self.window_width}x{self.window_height}+{x}+{y}')
        
        # Create main container with padding
        container = tk.Frame(self.window, bg='#1e1e1e', padx=20, pady=15)
        container.pack(fill='both', expand=True)
        
        # Recording indicator container
        indicator_frame = tk.Frame(container, bg='#1e1e1e')
        indicator_frame.pack(side='top', fill='x', pady=(0, 10))
        
        # Recording status with animated indicator
        self.recording_canvas = tk.Canvas(
            indicator_frame, 
            width=30, 
            height=30, 
            bg='#1e1e1e',
            highlightthickness=0
        )
        self.recording_canvas.pack(side='left', padx=(0, 10))
        
        # Status label
        self.status_label = tk.Label(
            indicator_frame,
            text="Ready to listen...",
            fg='#888888',
            bg='#1e1e1e',
            font=('SF Pro Display', 11)
        )
        self.status_label.pack(side='left')
        
        # Audio visualizer container
        visualizer_frame = tk.Frame(container, bg='#1e1e1e', height=40)
        visualizer_frame.pack(fill='x', pady=(0, 10))
        
        # Create audio level bars
        self.audio_canvas = tk.Canvas(
            visualizer_frame,
            height=40,
            bg='#1e1e1e',
            highlightthickness=0
        )
        self.audio_canvas.pack(fill='x')
        
        # Initialize audio bars (will be drawn dynamically)
        self.num_bars = 60
        self.bar_width = 8
        self.bar_spacing = 3
        self.bar_max_height = 35
        
        # Transcription display area
        text_frame = tk.Frame(container, bg='#2d2d2d', relief='flat')
        text_frame.pack(fill='both', expand=True)
        
        # Text display with modern styling
        self.text_display = tk.Text(
            text_frame,
            height=3,
            wrap='word',
            bg='#2d2d2d',
            fg='#ffffff',
            font=('SF Pro Text', 14),
            relief='flat',
            padx=15,
            pady=8,
            insertbackground='#4a9eff',
            selectbackground='#4a9eff',
            selectforeground='#ffffff'
        )
        self.text_display.pack(fill='both', expand=True)
        
        # Add subtle border
        text_frame.configure(highlightbackground='#3d3d3d', highlightthickness=1)
        
        # Make window draggable
        self._make_draggable()
        
        # Close button (subtle X in corner)
        close_btn = tk.Label(
            self.window,
            text='×',
            fg='#666666',
            bg='#1e1e1e',
            font=('SF Pro Display', 18),
            cursor='hand2'
        )
        close_btn.place(x=self.window_width-25, y=5)
        close_btn.bind('<Button-1>', lambda e: self.hide())
        
        # Start the UI update loop
        self.window.after(50, self._process_updates)
        
    def _make_draggable(self):
        """Make the window draggable"""
        def start_move(event):
            self.window.x = event.x
            self.window.y = event.y
            
        def on_move(event):
            deltax = event.x - self.window.x
            deltay = event.y - self.window.y
            x = self.window.winfo_x() + deltax
            y = self.window.winfo_y() + deltay
            self.window.geometry(f"+{x}+{y}")
            
        self.window.bind('<Button-1>', start_move)
        self.window.bind('<B1-Motion>', on_move)
        
    def show(self):
        """Show the overlay window"""
        if self.window is None:
            self.create_window()
        self.window.deiconify()
        self.window.lift()
        
    def hide(self):
        """Hide the overlay window"""
        if self.window:
            self.window.withdraw()
            
    def start_recording_animation(self):
        """Start the recording animation"""
        self.is_recording = True
        self._stop_animation.clear()
        
        # Update status
        self.update_queue.put(('status', 'Listening...'))
        
        # Start animation thread
        if self.animation_thread is None or not self.animation_thread.is_alive():
            self.animation_thread = threading.Thread(target=self._animate_recording)
            self.animation_thread.daemon = True
            self.animation_thread.start()
            
    def stop_recording_animation(self):
        """Stop the recording animation"""
        self.is_recording = False
        self._stop_animation.set()
        self.update_queue.put(('status', 'Processing...'))
        
    def _animate_recording(self):
        """Animate the recording indicator"""
        angle = 0
        while self.is_recording and not self._stop_animation.is_set():
            # Queue animation frame update
            self.update_queue.put(('animate', angle))
            angle = (angle + 10) % 360
            time.sleep(0.05)
            
        # Clear the indicator when stopped
        self.update_queue.put(('clear_animation', None))
        
    def _draw_recording_indicator(self, angle):
        """Draw animated recording indicator"""
        if not self.recording_canvas:
            return
            
        self.recording_canvas.delete('all')
        cx, cy = 15, 15
        
        # Draw pulsing circle
        pulse = abs(math.sin(math.radians(angle * 2)))
        radius = 8 + pulse * 2
        
        # Outer glow
        self.recording_canvas.create_oval(
            cx - radius - 2, cy - radius - 2,
            cx + radius + 2, cy + radius + 2,
            fill='', outline='#ff4444', width=1
        )
        
        # Inner circle (pulsing)
        self.recording_canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill='#ff4444', outline=''
        )
        
        # Center dot
        self.recording_canvas.create_oval(
            cx - 3, cy - 3,
            cx + 3, cy + 3,
            fill='#ffffff', outline=''
        )
        
    def update_transcription(self, text: str, is_final: bool = False):
        """Update the transcription display"""
        self.current_text = text
        if is_final:
            self.update_queue.put(('text_final', text))
            self.update_queue.put(('status', 'Ready to listen...'))
        else:
            self.update_queue.put(('text_partial', text))
        
        # Adjust window height based on text length
        self._adjust_window_size(text)
    
    def update_audio_levels(self, audio_data: np.ndarray):
        """Update audio level visualization"""
        if audio_data is not None and len(audio_data) > 0:
            # Calculate RMS for volume level
            rms = np.sqrt(np.mean(audio_data**2))
            # Convert to dB
            db = 20 * np.log10(max(rms, 1e-10))
            # Normalize to 0-1 range
            normalized = max(0, min(1, (db + 60) / 60))
            
            # Create frequency spectrum for visualization
            fft = np.fft.rfft(audio_data)
            magnitude = np.abs(fft)
            
            # Downsample to number of bars
            if len(magnitude) > self.num_bars:
                chunk_size = len(magnitude) // self.num_bars
                bars = []
                for i in range(self.num_bars):
                    chunk = magnitude[i*chunk_size:(i+1)*chunk_size]
                    if len(chunk) > 0:
                        bars.append(np.mean(chunk))
                    else:
                        bars.append(0)
                
                # Normalize bars
                max_val = max(bars) if bars and max(bars) > 0 else 1
                normalized_bars = [min(1, b/max_val) for b in bars]
                
                self.update_queue.put(('audio_levels', normalized_bars))
    
    def _adjust_window_size(self, text: str):
        """Dynamically adjust window size based on content"""
        if not self.window:
            return
            
        # Calculate required height based on text length
        text_lines = len(text) // 60 + 1  # Approximate lines needed
        min_height = 180
        max_height = 400
        
        # Base height + extra for each line of text
        new_height = min(max_height, min_height + (text_lines * 20))
        
        if abs(new_height - self.window_height) > 20:  # Only resize if significant change
            self.window_height = new_height
            self.update_queue.put(('resize', new_height))
    
    def _draw_audio_levels(self, levels: List[float]):
        """Draw audio level visualization bars"""
        if not self.audio_canvas:
            return
            
        self.audio_canvas.delete('all')
        
        canvas_width = self.audio_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = self.window_width - 40
            
        # Calculate bar positions
        total_bar_width = self.bar_width + self.bar_spacing
        start_x = (canvas_width - (self.num_bars * total_bar_width)) // 2
        
        for i, level in enumerate(levels[:self.num_bars]):
            x = start_x + (i * total_bar_width)
            height = max(3, level * self.bar_max_height)
            y = (40 - height) // 2
            
            # Color gradient based on level
            if level > 0.7:
                color = '#ff4444'  # Red for high levels
            elif level > 0.4:
                color = '#ffa500'  # Orange for medium
            else:
                color = '#4a9eff'  # Blue for low
            
            # Draw bar with rounded corners effect
            self.audio_canvas.create_rectangle(
                x, y + height//4,
                x + self.bar_width, y + height,
                fill=color,
                outline='',
                tags='bar'
            )
            
            # Add glow effect for active bars
            if level > 0.1:
                self.audio_canvas.create_rectangle(
                    x - 1, y + height//4 - 1,
                    x + self.bar_width + 1, y + height + 1,
                    fill='',
                    outline=color,
                    width=1,
                    tags='glow'
                )
            
    def _process_updates(self):
        """Process queued updates in the main thread"""
        try:
            while not self.update_queue.empty():
                update_type, data = self.update_queue.get_nowait()
                
                if update_type == 'status':
                    self.status_label.config(text=data)
                    if data == 'Listening...':
                        self.status_label.config(fg='#4a9eff')
                    elif data == 'Processing...':
                        self.status_label.config(fg='#ffa500')
                    else:
                        self.status_label.config(fg='#888888')
                        
                elif update_type == 'animate':
                    self._draw_recording_indicator(data)
                    
                elif update_type == 'clear_animation':
                    self.recording_canvas.delete('all')
                    
                elif update_type == 'text_partial':
                    self.text_display.delete('1.0', 'end')
                    self.text_display.insert('1.0', data)
                    self.text_display.config(fg='#cccccc')  # Gray for partial
                    
                elif update_type == 'text_final':
                    self.text_display.delete('1.0', 'end')
                    self.text_display.insert('1.0', data)
                    self.text_display.config(fg='#ffffff')  # White for final
                    
                elif update_type == 'audio_levels':
                    self._draw_audio_levels(data)
                    
                elif update_type == 'resize':
                    # Smoothly resize window
                    current_geo = self.window.geometry()
                    current_height = int(current_geo.split('x')[1].split('+')[0])
                    if abs(current_height - data) > 10:
                        geo_parts = current_geo.split('+')
                        new_geo = f"{self.window_width}x{data}+{geo_parts[1]}+{geo_parts[2]}"
                        self.window.geometry(new_geo)
                    
        except queue.Empty:
            pass
            
        # Schedule next update
        if self.window:
            self.window.after(50, self._process_updates)
            
    def destroy(self):
        """Clean up the window"""
        self._stop_animation.set()
        if self.window:
            self.window.destroy()
            self.window = None


class ModernMenuBarIcon:
    """
    Modern menu bar icon with visual feedback
    """
    
    def __init__(self, rumps_app):
        self.app = rumps_app
        self.is_recording = False
        
        # Icons for different states
        self.icon_idle = "🎙️"  # Microphone emoji
        self.icon_recording = "🔴"  # Red circle for recording
        self.icon_processing = "⏳"  # Hourglass for processing
        
    def set_idle(self):
        """Set icon to idle state"""
        self.is_recording = False
        self.app.icon = self.icon_idle
        self.app.title = ""
        
    def set_recording(self):
        """Set icon to recording state"""
        self.is_recording = True
        self.app.icon = self.icon_recording
        self.app.title = " Recording"
        
    def set_processing(self):
        """Set icon to processing state"""
        self.is_recording = False
        self.app.icon = self.icon_processing
        self.app.title = " Processing"


# Integration helper for the main whisper_dictation.py
class UIManager:
    """
    Manager class to coordinate all UI components
    """
    
    def __init__(self, rumps_app=None):
        self.overlay = TranscriptionOverlay()
        self.menu_icon = ModernMenuBarIcon(rumps_app) if rumps_app else None
        self.is_active = False
        self.tk_root = None
        
    def start_recording(self):
        """Start recording UI feedback"""
        self.is_active = True
        if self.menu_icon:
            self.menu_icon.set_recording()
        self.overlay.show()
        self.overlay.start_recording_animation()
        
    def stop_recording(self):
        """Stop recording UI feedback"""
        if self.menu_icon:
            self.menu_icon.set_processing()
        self.overlay.stop_recording_animation()
        
    def update_transcription(self, text: str, is_final: bool = False):
        """Update transcription display"""
        self.overlay.update_transcription(text, is_final)
        if is_final and self.menu_icon:
            self.menu_icon.set_idle()
            # Auto-hide after showing final result for 3 seconds
            if self.is_active:
                threading.Timer(3.0, self._auto_hide).start()
                
    def update_audio_levels(self, audio_data: np.ndarray):
        """Update audio visualization"""
        if self.is_active:
            self.overlay.update_audio_levels(audio_data)
                
    def _auto_hide(self):
        """Auto-hide the overlay after displaying result"""
        if not self.overlay.is_recording:
            self.overlay.hide()
            self.is_active = False
            
    def cleanup(self):
        """Clean up UI resources"""
        self.overlay.destroy()