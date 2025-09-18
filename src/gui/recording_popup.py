"""
Recording Popup GUI for Whisper Voice Recognition System
Uses PyQt6 for proper floating window without dock icon on macOS
"""

from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont, QPen, QBrush
import sys
import time
import random
import math
import threading
from typing import Optional, Callable
from datetime import timedelta


class RecordingPopup(QWidget):
    """
    A recording popup using PyQt6 with:
    - Gradient background (blue to purple)
    - Speech Recording title
    - Dynamic waveform visualization
    - Timer display
    - File name display
    - No dock icon on macOS
    """

    # Signal for thread-safe audio level updates
    audio_level_signal = pyqtSignal(float)

    def __init__(self, on_stop_callback: Optional[Callable] = None, on_cancel_callback: Optional[Callable] = None):
        """
        Initialize the recording popup

        Args:
            on_stop_callback: Function to call when recording stops
            on_cancel_callback: Function to call when cancelled
        """
        # Ensure QApplication exists
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        super().__init__()

        self.on_stop_callback = on_stop_callback
        self.on_cancel_callback = on_cancel_callback
        self.is_visible = False
        self.stop_animation = False

        # Recording state
        self.start_time = None
        self.recording_file = "Project-Meeting-Notes.wav"

        # Waveform data and animation
        self.phase = 0.0  # Animation phase for pulsing
        self.audio_levels = [0.0] * 30  # 30 points for smooth waveform
        self.current_level = 0.0
        self.level_lock = threading.Lock()

        # Connect signal for thread-safe updates
        self.audio_level_signal.connect(self._update_audio_level_internal)

        # Setup window
        self._setup_window()

        # Timer for continuous animation (pulsing and waveform)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        
        # Timer for timer display
        self.timer_update = QTimer()
        self.timer_update.timeout.connect(self._update_timer_display)

    def _setup_window(self):
        """Setup window properties for floating popup without dock icon"""
        # Critical flags for no dock icon on macOS and persistent display
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |  # Always on top
            Qt.WindowType.FramelessWindowHint |  # No title bar
            Qt.WindowType.Tool |  # Tool window (no dock icon on macOS)
            Qt.WindowType.WindowDoesNotAcceptFocus  # Never take focus
        )

        # Window properties for transparency and material design
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)  # macOS specific
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Accept mouse events
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)  # Force always on top

        # Set window opacity for transparency effect
        self.setWindowOpacity(0.95)  # Slight transparency

        # Prevent focus stealing - critical for paste functionality
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Responsive size based on screen dimensions
        if self.app:
            screen = self.app.primaryScreen()
            if screen:
                screen_rect = screen.geometry()
                # Scale based on screen width (base: 1920px)
                scale_factor = min(screen_rect.width() / 1920.0, screen_rect.height() / 1080.0)
                scale_factor = max(0.7, min(1.2, scale_factor))  # Clamp between 70%-120%
                
                # Base size (more rectangular - wider and less tall)
                base_width = 500
                base_height = 280
                
                # Apply scaling
                popup_width = int(base_width * scale_factor)
                popup_height = int(base_height * scale_factor)
                
                self.setFixedSize(popup_width, popup_height)
                
                # Center on screen
                x = (screen_rect.width() - popup_width) // 2
                y = (screen_rect.height() - popup_height) // 2 - int(100 * scale_factor)
                self.move(x, y)
            else:
                # Fallback if no screen info
                self.setFixedSize(500, 280)

    def _update_animation(self):
        """Update animation phase for pulsing effects and waveform movement"""
        if self.is_visible and not self.stop_animation:
            self.phase += 0.05  # Continuous phase update for smooth animations
            self.update()  # Trigger repaint  # Trigger repaint

    def show(self):
        """Display the recording popup"""
        if self.is_visible:
            return

        self.is_visible = True
        self.stop_animation = False
        self.start_time = time.time()
        self.phase = 0.0  # Reset phase for fresh animation

        # Start animations
        self.animation_timer.start(50)  # 20 FPS for smooth pulsing
        self.timer_update.start(10)  # Update timer every 10ms

        # Show window without stealing focus
        super().show()
        # Don't call raise_() or activateWindow() - those steal focus!
        # The WindowStaysOnTopHint flag handles staying on top

        print(f"🔴 Recording popup displayed")
    def hide(self):
        """Hide the recording popup"""
        if not self.is_visible:
            return

        self.stop_animation = True
        self.is_visible = False

        # Stop timers
        self.animation_timer.stop()
        self.timer_update.stop()

        # Hide window
        super().hide()

        print("⚫ Recording popup hidden")

    def paintEvent(self, event):
        """Paint the popup with material design styling"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw frosted glass background
        self._draw_frosted_background(painter)
        
        # Draw glowing neon border around entire popup
        self._draw_neon_border(painter)
        
        # Content area (adjusted for new rectangular dimensions)
        content_rect = QRectF(25, 20, self.width() - 50, self.height() - 40)

        # Draw waveform (positioned higher without title)
        waveform_rect = QRectF(content_rect.x() + 20, content_rect.y() + 40, 
                              content_rect.width() - 40, 100)
        self._draw_waveform(painter, waveform_rect)

        # Draw timer with rounded background
        if self.start_time:
            elapsed = time.time() - self.start_time
            time_str = self._format_time(elapsed)
        else:
            time_str = "00:00"  # Fixed default format

        # Timer background with rounded corners (centered for new layout)
        timer_bg_rect = QRectF(content_rect.center().x() - 100, content_rect.y() + 160, 200, 45)
        timer_bg_color = QColor(0, 255, 255, 40)  # Subtle cyan background
        painter.setBrush(QBrush(timer_bg_color))
        painter.setPen(QPen(QColor(0, 255, 255, 100), 1))
        painter.drawRoundedRect(timer_bg_rect, 15, 15)

        # Timer text
        painter.setPen(QPen(QColor(0, 255, 255)))  # Cyan color like reference
        timer_font = QFont("SF Mono", 24, QFont.Weight.Bold)
        painter.setFont(timer_font)
        painter.drawText(timer_bg_rect, Qt.AlignmentFlag.AlignCenter, time_str)
        
        # Draw microphone icon at bottom center
        self._draw_microphone_icon(painter, content_rect)



    def _draw_material_surface(self, painter):
        """Draw material design background with subtle transparency"""
        # Subtle frosted glass effect background
        background_color = QColor(250, 250, 250, 240)  # Very light gray with transparency
        painter.fillRect(self.rect(), QBrush(background_color))

    def _draw_frosted_background(self, painter):
        """Draw frosted glass background with blur effect for visibility"""
        # Draw dark blur background for better contrast
        bg_rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        
        # Create blur effect with dark background
        # First layer - dark blur backdrop
        blur_color = QColor(0, 0, 0, 80)  # Dark background with opacity
        painter.setBrush(QBrush(blur_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(bg_rect, 20, 20)
        
        # Second layer - frosted glass effect
        frosted_color = QColor(255, 255, 255, 15)  # Very subtle white frost
        painter.setBrush(QBrush(frosted_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawRoundedRect(bg_rect, 20, 20)

    def _draw_neon_border(self, painter):
        """Draw glowing neon border with shiny gradient effect"""
        # Continuous pulsing animation
        pulse_phase = self.phase * 2.0  # Faster pulsing
        pulse_intensity = 0.7 + (math.sin(pulse_phase) * 0.3)  # Pulse between 0.7 and 1.0
        
        # Popup rectangle with rounded corners
        popup_rect = QRectF(5, 5, self.width() - 10, self.height() - 10)
        
        # Draw multiple border layers for shiny gradient glow effect
        for i in range(6):  # Fewer layers for thinner border
            # Calculate opacity based on layer and pulse
            base_alpha = 220 - (i * 35)
            alpha = int(base_alpha * pulse_intensity)
            
            # Thinner border widths
            width = 2.0 + (5 - i) * 0.4  # Much thinner
            
            # Shinier gradient colors - cyan to pink/magenta
            if i < 2:
                # Inner layers - bright electric cyan
                color = QColor(0, 255, 255, alpha)
            elif i < 3:
                # Middle layer - cyan to pink transition
                color = QColor(100, 255, 255, alpha)
            elif i < 4:
                # Pink/magenta layer
                color = QColor(255, 100, 255, int(alpha * 0.9))
            else:
                # Outer layers - purple/pink glow
                color = QColor(255, 150, 255, int(alpha * 0.5))
                
            painter.setPen(QPen(color, width))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            
            # Adjust rect for each layer
            offset = i * 0.4  # Smaller offset for thinner border
            painter.drawRoundedRect(
                popup_rect.adjusted(offset, offset, -offset, -offset), 
                20, 20
            )

    def _draw_waveform(self, painter, waveform_rect=None):
        """Draw animated waveform with dramatic music visualizer effect"""
        # Use provided rect or default for backward compatibility
        if waveform_rect is None:
            waveform_rect = QRectF(75, 100, 450, 80)
        
        center_y = waveform_rect.center().y()

        # Draw waveform bars with clean varied heights
        with self.level_lock:
            levels = self.audio_levels[:]

        num_bars = 60  # More bars for finer detail
        bar_width = waveform_rect.width() / num_bars
        bar_spacing = bar_width * 0.4  # Much more spacing for narrower bars
        
        import random
        
        for i in range(num_bars):
            x = waveform_rect.left() + (i * bar_width) + bar_spacing
            
            # Get interpolated audio level
            level_index = int((i / num_bars) * len(levels))
            level = levels[min(level_index, len(levels) - 1)]
            
            # MORE DRAMATIC height variations
            # Different frequency bands with more extreme differences
            if i < num_bars * 0.15:  # Sub-bass - very tall
                base_height = 0.9
                wave_freq = 0.1
                amplitude_mult = 1.3
            elif i < num_bars * 0.3:  # Bass - tall
                base_height = 0.75
                wave_freq = 0.15
                amplitude_mult = 1.2
            elif i < num_bars * 0.6:  # Mids - medium with variation
                base_height = 0.5
                wave_freq = 0.25
                amplitude_mult = 1.0
            elif i < num_bars * 0.8:  # High mids - shorter
                base_height = 0.35
                wave_freq = 0.35
                amplitude_mult = 0.8
            else:  # Highs - very short but active
                base_height = 0.2
                wave_freq = 0.5
                amplitude_mult = 0.6
            
            # Much more dramatic wave pattern with faster movement
            wave_pattern = math.sin(i * wave_freq + self.phase * 3.0) * 0.6 + 0.4
            
            # More chaotic randomness for dramatic jumps
            random.seed(i * 1337 + int(self.phase * 0.5))
            random_factor = random.random() * 0.7 + 0.3  # 0.3 to 1.0
            
            # Additional dramatic pulse wave
            pulse_wave = math.sin(self.phase * 4.0 + i * 0.1) * 0.3
            
            # Calculate bar height with all factors
            min_height = 2
            max_height = waveform_rect.height() * 0.95
            
            # Combine all factors for dramatic effect
            height_factor = base_height * wave_pattern * random_factor * amplitude_mult
            height_factor += pulse_wave  # Add pulse for more movement
            
            # Dramatic breathing effect
            breath = 0.85 + (math.sin(self.phase * 2.5 + i * 0.05) * 0.15)
            height_factor *= breath
            
            # Ensure within bounds
            height_factor = max(0.05, min(1.0, height_factor))
            
            amplitude = min_height + (max_height - min_height) * height_factor
            
            # Add audio level influence (but keep animation even when silent)
            amplitude = amplitude * (0.5 + level * 0.5)
            
            # Ensure minimum visibility
            amplitude = max(min_height, min(amplitude, max_height))
            
            # Draw narrower vertical bar
            bar_rect = QRectF(
                x, 
                center_y - amplitude/2, 
                bar_width * 0.3,  # Much narrower bars (30% of spacing)
                amplitude
            )
            
            # Solid cyan color for clean look
            painter.fillRect(bar_rect, QBrush(QColor(0, 255, 255, 200)))

    def _draw_microphone_icon(self, painter, content_rect):
        """Draw microphone icon at bottom center of popup"""
        # Icon position at bottom center
        icon_x = content_rect.center().x()
        icon_y = content_rect.bottom() - 20
        
        # Draw microphone shape with glow effect
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Outer glow
        for i in range(3):
            alpha = 60 - i * 20
            size = 16 + i * 2
            painter.setPen(QPen(QColor(0, 255, 255, alpha), 2))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            
            # Microphone body (rounded rectangle)
            mic_rect = QRectF(icon_x - size/2, icon_y - size, size, size * 1.5)
            painter.drawRoundedRect(mic_rect, size/2, size/2)
        
        # Main microphone icon
        painter.setPen(QPen(QColor(0, 255, 255, 200), 2))
        painter.setBrush(QBrush(QColor(0, 255, 255, 100)))
        
        # Microphone body
        mic_rect = QRectF(icon_x - 7, icon_y - 14, 14, 20)
        painter.drawRoundedRect(mic_rect, 7, 7)
        
        # Microphone stand
        painter.setPen(QPen(QColor(0, 255, 255, 200), 2))
        painter.drawLine(QPointF(icon_x, icon_y + 6), QPointF(icon_x, icon_y + 12))
        
        # Microphone base
        painter.drawLine(QPointF(icon_x - 8, icon_y + 12), QPointF(icon_x + 8, icon_y + 12))
        
        # Microphone arc (sound capture area)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        arc_rect = QRectF(icon_x - 12, icon_y - 10, 24, 24)
        painter.drawArc(arc_rect, 30 * 16, 120 * 16)  # Arc from 30 to 150 degrees

    def _format_time(self, seconds: float) -> str:
        """Format seconds into MM:SS format"""
        if seconds is None:
            return "00:00"
        td = timedelta(seconds=seconds)
        minutes = int(td.total_seconds() // 60)
        secs = int(td.total_seconds() % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _update_timer_display(self):
        """Update timer display (triggers repaint)"""
        if self.is_visible and not self.stop_animation:
            self.update()  # Trigger repaint

    def update_audio_level(self, level: float):
        """
        Update audio level from any thread

        Args:
            level: Audio level (0.0 to 1.0)
        """
        # Emit signal for thread-safe update
        self.audio_level_signal.emit(level)

    def _update_audio_level_internal(self, level: float):
        """
        Internal method to update audio level (called via signal)

        Args:
            level: Audio level (0.0 to 1.0)
        """
        with self.level_lock:
            self.current_level = max(0.0, min(1.0, level))
            # Shift buffer and add new level
            self.audio_levels = self.audio_levels[1:] + [self.current_level]

    def is_showing(self) -> bool:
        """Check if popup is currently visible"""
        return self.is_visible

    def focusOutEvent(self, event):
        """Override to prevent hiding when focus is lost"""
        # Do nothing - keep window visible
        event.ignore()
        # Ensure we stay on top
        if self.is_visible:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            super().show()

    def changeEvent(self, event):
        """Override to prevent hiding on deactivation"""
        # Ignore window state changes that would hide the popup
        if event.type() == event.Type.WindowStateChange:
            event.ignore()
            # Ensure we stay visible and on top
            if self.is_visible:
                self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                super().show()
        else:
            super().changeEvent(event)

    def mousePressEvent(self, event):
        """Override to prevent focus stealing on click"""
        # Handle the event but don't take focus
        super().mousePressEvent(event)
        # Prevent focus from being taken
        event.accept()

    def _on_stop_clicked(self):
        """Handle stop action"""
        print("✅ Stop clicked")
        if self.on_stop_callback:
            self.on_stop_callback()
        self.hide()

    def _on_cancel_clicked(self):
        """Handle cancel action"""
        print("❌ Recording cancelled")
        if self.on_cancel_callback:
            self.on_cancel_callback()
        self.hide()


class RecordingPopupManager:
    """
    Manager for recording popup with audio monitoring integration
    Handles lifecycle and audio level updates
    """

    def __init__(self):
        """Initialize the popup manager"""
        self.popup: Optional[RecordingPopup] = None
        self.audio_monitor = None
        self.stop_callback = None
        self.cancel_callback = None

    def set_callbacks(self, stop_callback: Optional[Callable] = None, cancel_callback: Optional[Callable] = None):
        """Set callbacks for stop and cancel actions"""
        self.stop_callback = stop_callback
        self.cancel_callback = cancel_callback

    def show_recording_popup(self):
        """Show the recording popup with real-time audio monitoring"""
        if self.popup and self.popup.is_showing():
            return  # Already showing

        try:
            # Import audio monitor here to avoid circular imports
            from ..utils.audio_monitor import AudioLevelMonitor

            # Create popup with callbacks
            self.popup = RecordingPopup(
                on_stop_callback=self.stop_callback,
                on_cancel_callback=self.cancel_callback
            )

            # Start audio monitoring in background thread
            def start_audio_monitoring():
                self.audio_monitor = AudioLevelMonitor(callback=self.popup.update_audio_level)
                self.audio_monitor.start_monitoring()

            monitor_thread = threading.Thread(target=start_audio_monitoring, daemon=True)
            monitor_thread.start()

            # Show the popup
            self.popup.show()

            print("🔴 Recording popup displayed with audio monitoring")

        except Exception as e:
            print(f"Error showing recording popup: {e}")

    def hide_recording_popup(self):
        """Hide the recording popup and stop audio monitoring"""
        # Prevent double cleanup
        if self.popup is None and self.audio_monitor is None:
            return
            
        if self.popup:
            try:
                self.popup.hide()
            except Exception as e:
                print(f"Error hiding popup: {e}")
            finally:
                self.popup = None

        if self.audio_monitor:
            try:
                self.audio_monitor.stop_monitoring()
            except Exception as e:
                print(f"Error stopping audio monitor: {e}")
            finally:
                self.audio_monitor = None
                
        print("⚫ Recording stopped")


# Global popup manager instance
popup_manager = RecordingPopupManager()

# Convenience functions for easy integration
def show_recording_popup(stop_callback: Optional[Callable] = None, cancel_callback: Optional[Callable] = None):
    """Show recording popup with optional callbacks"""
    popup_manager.set_callbacks(stop_callback, cancel_callback)
    popup_manager.show_recording_popup()

def hide_recording_popup():
    """Hide recording popup"""
    popup_manager.hide_recording_popup()

def is_recording_popup_visible() -> bool:
    """Check if recording popup is visible"""
    return popup_manager.popup and popup_manager.popup.is_showing()