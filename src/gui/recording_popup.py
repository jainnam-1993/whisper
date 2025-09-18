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

        # Calculate scale factor for responsive layout
        base_height = 280  # Reference height from _setup_window
        scale_factor = self.height() / base_height

        # Position waveform proportionally (30% from top of content area)
        waveform_y_offset = content_rect.height() * 0.2  # 20% down from top
        waveform_height = min(100 * scale_factor, content_rect.height() * 0.35)  # Max 35% of height
        waveform_rect = QRectF(
            content_rect.x() + 20,
            content_rect.y() + waveform_y_offset,
            content_rect.width() - 40,
            waveform_height
        )
        self._draw_waveform(painter, waveform_rect)

        # Draw particle dots around waveform
        self._draw_particle_dots(painter, waveform_rect)

        # Draw timer with rounded background
        if self.start_time:
            elapsed = time.time() - self.start_time
            time_str = self._format_time(elapsed)
        else:
            time_str = "00:00"  # Fixed default format

        # Position timer relative to waveform bottom with scaled gap
        timer_gap = 20 * scale_factor  # Scale the gap between waveform and timer
        timer_y = waveform_rect.bottom() + timer_gap

        # Ensure timer doesn't go too low (leave space for microphone icon)
        max_timer_y = content_rect.bottom() - (80 * scale_factor)  # Reserve space for mic
        timer_y = min(timer_y, max_timer_y)

        # Timer dimensions with scaling
        timer_width = 120 * scale_factor
        timer_height = 45 * scale_factor

        # Timer background with rounded corners (centered horizontally)
        timer_bg_rect = QRectF(
            content_rect.center().x() - timer_width/2,
            timer_y,
            timer_width,
            timer_height
        )
        timer_bg_color = QColor(51, 193, 255, 30)  # Subtle cyan background
        painter.setBrush(QBrush(timer_bg_color))
        painter.setPen(QPen(QColor(51, 193, 255, 100), 1))
        painter.drawRoundedRect(timer_bg_rect, timer_height/2, timer_height/2)  # Pill shape

        # Timer text with scaled font
        painter.setPen(QPen(QColor(51, 193, 255)))  # Cyan color #33C1FF
        timer_font_size = int(20 * scale_factor)
        timer_font = QFont("SF Mono", timer_font_size, QFont.Weight.Bold)
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
        """Draw a semi-transparent dark background for the frosted glass effect."""
        bg_rect = QRectF(8, 8, self.width() - 16, self.height() - 16)
        background_color = QColor(10, 20, 35, 200)  # Dark blue, semi-transparent
        painter.setBrush(QBrush(background_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg_rect, 30, 30)

    def _draw_neon_border(self, painter):
        """Draw a clean, glowing cyan border to match the reference design."""
        popup_rect = QRectF(8, 8, self.width() - 16, self.height() - 16)

        # Outer glow effect (subtle)
        glow_color = QColor(51, 193, 255, 80)
        painter.setPen(QPen(glow_color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(popup_rect, 30, 30)

        # Main border line
        border_color = QColor(51, 193, 255, 255)  # #33C1FF - exact cyan
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(popup_rect, 30, 30)

    def _draw_waveform(self, painter, waveform_rect=None):
        """Draw symmetric waveform matching reference design"""
        # Use provided rect or default for backward compatibility
        if waveform_rect is None:
            waveform_rect = QRectF(75, 100, 450, 80)

        center_y = waveform_rect.center().y()

        # Draw waveform bars with clean varied heights
        with self.level_lock:
            levels = self.audio_levels[:]

        num_bars = 60  # Number of bars
        total_width = waveform_rect.width()
        bar_width = 3  # Fixed bar width in pixels
        spacing = 2  # Fixed spacing between bars

        # Calculate total space needed and center the bars
        total_bars_width = (bar_width + spacing) * num_bars
        start_x = waveform_rect.left() + (total_width - total_bars_width) / 2

        import random

        # Set pen and brush once for all bars
        painter.setPen(Qt.PenStyle.NoPen)  # No outline
        bar_brush = QBrush(QColor(51, 193, 255, 255))  # #33C1FF - cyan from reference
        painter.setBrush(bar_brush)

        for i in range(num_bars):
            x = start_x + i * (bar_width + spacing)

            # Get interpolated audio level
            level_index = int((i / num_bars) * len(levels))
            level = levels[min(level_index, len(levels) - 1)]

            # Create tapered structure from center to edges
            distance_from_center = abs(i - num_bars / 2) / (num_bars / 2)

            # Taper heights - tallest in center, shortest at edges
            if distance_from_center < 0.2:  # Core - center 20%
                base_height = 0.9
            elif distance_from_center < 0.5:  # Body - middle sections
                base_height = 0.7 - (distance_from_center - 0.2) * 2
            elif distance_from_center < 0.8:  # Tails
                base_height = 0.3 - (distance_from_center - 0.5) * 0.5
            else:  # Far edges - dots
                base_height = 0.05

            # Smooth wave animation
            wave_pattern = math.sin(i * 0.2 + self.phase * 2.0) * 0.2 + 0.8

            # Subtle randomness for organic feel
            random.seed(i * 1337 + int(self.phase * 0.3))
            random_factor = random.random() * 0.2 + 0.8  # 0.8 to 1.0

            # Calculate bar height
            min_height = 2
            max_height = waveform_rect.height() * 0.45  # Half height for symmetry

            # Combine factors
            height_factor = base_height * wave_pattern * random_factor

            # Gentle breathing effect
            breath = 0.9 + (math.sin(self.phase * 2.0 + i * 0.05) * 0.1)
            height_factor *= breath

            # Ensure within bounds
            height_factor = max(0.02, min(1.0, height_factor))

            half_amplitude = min_height + (max_height - min_height) * height_factor

            # Add audio level influence
            half_amplitude = half_amplitude * (0.6 + level * 0.4)

            # Ensure minimum visibility
            half_amplitude = max(min_height, min(half_amplitude, max_height))

            # Draw symmetric bars (top and bottom from center)
            # Top bar
            top_rect = QRectF(
                x,
                center_y - half_amplitude,
                bar_width,
                half_amplitude
            )
            painter.fillRect(top_rect, bar_brush)

            # Bottom bar (mirror)
            bottom_rect = QRectF(
                x,
                center_y,
                bar_width,
                half_amplitude
            )
            painter.fillRect(bottom_rect, bar_brush)

    def _draw_particle_dots(self, painter, waveform_rect):
        """Draw floating particle dots around waveform for dynamic effect"""
        import random

        # Set random seed based on phase for animated particles
        random.seed(int(self.phase * 10))

        # Draw 30-40 particle dots
        num_particles = 35

        for i in range(num_particles):
            # Random position around waveform
            # Concentrate particles near the center
            x_offset = (random.random() - 0.5) * waveform_rect.width() * 1.2
            y_offset = (random.random() - 0.5) * waveform_rect.height() * 1.5

            # Position relative to waveform center
            x = waveform_rect.center().x() + x_offset
            y = waveform_rect.center().y() + y_offset

            # Vary particle size and opacity
            size = random.random() * 2 + 1  # 1-3 pixels
            base_alpha = random.randint(20, 80)

            # Pulse effect for particles
            pulse = math.sin(self.phase * 3 + i) * 0.3 + 0.7
            alpha = int(base_alpha * pulse)

            # Draw particle dot
            particle_color = QColor(51, 193, 255, alpha)  # Cyan with varying opacity
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(particle_color))
            painter.drawEllipse(QPointF(x, y), size, size)

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
            painter.setPen(QPen(QColor(51, 193, 255, alpha), 2))  # Cyan #33C1FF
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

            # Microphone body (rounded rectangle)
            mic_rect = QRectF(icon_x - size/2, icon_y - size, size, size * 1.5)
            painter.drawRoundedRect(mic_rect, size/2, size/2)

        # Main microphone icon
        painter.setPen(QPen(QColor(51, 193, 255, 200), 2))  # Cyan
        painter.setBrush(QBrush(QColor(51, 193, 255, 100)))

        # Microphone body
        mic_rect = QRectF(icon_x - 7, icon_y - 14, 14, 20)
        painter.drawRoundedRect(mic_rect, 7, 7)

        # Microphone stand
        painter.setPen(QPen(QColor(51, 193, 255, 200), 2))
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