"""
Recording Popup GUI for Whisper Voice Recognition System
Uses PyQt6 for proper floating window without dock icon on macOS
"""

from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont, QPen, QBrush, QPixmap
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

        # Set window opacity for glassmorphism effect (more transparent)
        self.setWindowOpacity(0.75)  # 75% opacity for strong glass effect

        # Prevent focus stealing - critical for paste functionality
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Responsive size based on screen dimensions
        if self.app:
            # Get screen where cursor is (active monitor)
            cursor_pos = self.app.primaryScreen().availableGeometry().center()
            screen = self.app.screenAt(cursor_pos)
            
            # Fallback to primary if no screen detected at cursor
            if not screen:
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
                
                # Center on ACTIVE screen (not primary)
                x = screen_rect.x() + (screen_rect.width() - popup_width) // 2
                y = screen_rect.y() + (screen_rect.height() - popup_height) // 2 - int(100 * scale_factor)
                self.move(x, y)
            else:
                # Fallback if no screen info
                self.setFixedSize(500, 280)

    def _update_animation(self):
        """Update animation phase for pulsing effects and waveform movement"""
        if self.is_visible and not self.stop_animation:
            # Simple velocity-based easing without heavy computation
            if not hasattr(self, 'phase_velocity'):
                self.phase_velocity = 0.0
            
            # Smooth acceleration with minimal calculation
            target_velocity = 0.02
            self.phase_velocity += (target_velocity - self.phase_velocity) * 0.1
            self.phase += self.phase_velocity
            self.update()  # Trigger repaint

    def show(self):
        """Display the recording popup on active monitor"""
        if self.is_visible:
            return

        self.is_visible = True
        self.stop_animation = False
        self.start_time = time.time()
        self.phase = 0.0  # Reset phase for fresh animation

        # ====================================================================
        # CRITICAL: Position on active monitor BEFORE showing
        # ====================================================================
        self._position_on_active_monitor()

        # Start animations
        self.animation_timer.start(30)  # ~33 FPS for smoother rendering
        self.timer_update.start(10)  # Update timer every 10ms

        # Show window without stealing focus
        super().show()
        # Don't call raise_() or activateWindow() - those steal focus!
        # The WindowStaysOnTopHint flag handles staying on top

        print(f"🔴 Recording popup displayed on active monitor")
    
    def _position_on_active_monitor(self):
        """
        Position popup on the monitor where the cursor currently is.
        Called dynamically each time show() is invoked.
        """
        if not self.app:
            return
            
        from PyQt6.QtGui import QCursor
        
        # Get current cursor position
        cursor_pos = QCursor.pos()
        
        # Find which screen the cursor is on
        screen = self.app.screenAt(cursor_pos)
        
        # Fallback to primary screen if detection fails
        if not screen:
            screen = self.app.primaryScreen()
        
        if screen:
            screen_rect = screen.geometry()
            
            # Get current window size
            popup_width = self.width()
            popup_height = self.height()
            
            # Center on the active screen
            x = screen_rect.x() + (screen_rect.width() - popup_width) // 2
            y = screen_rect.y() + (screen_rect.height() - popup_height) // 2 - 100
            
            self.move(x, y)
            print(f"📍 Positioned on screen: {screen_rect.width()}x{screen_rect.height()} at ({x}, {y})")
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
        """Paint the popup with responsive ratio-based positioning"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw frosted glass background
        self._draw_frosted_background(painter)

        # Draw glowing neon border around entire popup
        self._draw_neon_border(painter)

        # Content area using ratios (5% padding on all sides)
        padding_ratio = 0.05
        content_rect = QRectF(
            self.width() * padding_ratio,
            self.height() * padding_ratio,
            self.width() * (1 - 2 * padding_ratio),
            self.height() * (1 - 2 * padding_ratio)
        )

        # Waveform positioning using pure ratios
        # Waveform at 25% from top, 35% height, 80% width
        waveform_rect = QRectF(
            content_rect.x() + content_rect.width() * 0.1,  # 10% margin from sides
            content_rect.y() + content_rect.height() * 0.25,  # 25% from top
            content_rect.width() * 0.8,  # 80% of content width
            content_rect.height() * 0.35  # 35% of content height
        )
        self._draw_waveform(painter, waveform_rect)

        # Draw timer with rounded background
        if self.start_time:
            elapsed = time.time() - self.start_time
            time_str = self._format_time(elapsed)
        else:
            time_str = "00:00"  # Fixed default format

        # Timer positioning using ratios
        # Timer at 70% from top, centered horizontally
        timer_width = content_rect.width() * 0.25  # 25% of content width
        timer_height = content_rect.height() * 0.15  # 15% of content height
        timer_y = content_rect.y() + content_rect.height() * 0.70  # 70% from top

        # No background for timer - clean minimal look
        timer_rect = QRectF(
            content_rect.center().x() - timer_width/2,
            timer_y + timer_height/4,  # Center text vertically
            timer_width,
            timer_height/2
        )
        
        # Timer text - bold and clean
        painter.setPen(QPen(QColor(16, 24, 32)))  # Almost black for strong contrast  # Cyan color #33C1FF
        timer_font_size = int(self.height() * 0.08)  # 8% of window height
        timer_font = QFont("Arial", timer_font_size, QFont.Weight.DemiBold)  # Cross-platform font  # Modern system font
        timer_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)  # Add letter spacing
        painter.setFont(timer_font)
        painter.drawText(timer_rect, Qt.AlignmentFlag.AlignCenter, time_str)

        # Draw microphone icon at bottom center
        self._draw_microphone_icon(painter, content_rect)





    def _draw_frosted_background(self, painter):
        """
        Draw glassmorphism background with blur effect and layered shadows
        
        Glassmorphism characteristics:
        - High transparency (60-70%)
        - Blur effect (background blur)
        - Double/triple shadow layers for depth
        - Subtle border for definition
        - Soft gradient overlay
        """
        # Main container using ratios (2% padding for tighter fit)
        padding_ratio = 0.02
        bg_rect = QRectF(
            self.width() * padding_ratio,
            self.height() * padding_ratio, 
            self.width() * (1 - 2 * padding_ratio),
            self.height() * (1 - 2 * padding_ratio)
        )
        
        corner_radius = min(self.width(), self.height()) * 0.06  # 6% corner radius
        
        # ====================================================================
        # LAYER 1: Outer shadow (furthest, most diffuse) - DARKER
        # ====================================================================
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))  # Much darker
        painter.setPen(Qt.PenStyle.NoPen)
        outer_shadow_rect = QRectF(
            bg_rect.x() + self.width() * 0.012,
            bg_rect.y() + self.height() * 0.018,
            bg_rect.width(),
            bg_rect.height()
        )
        painter.drawRoundedRect(outer_shadow_rect, corner_radius, corner_radius)
        
        # ====================================================================
        # LAYER 2: Mid shadow (creates depth) - DARKER
        # ====================================================================
        painter.setBrush(QBrush(QColor(0, 0, 0, 60)))  # Much darker
        mid_shadow_rect = QRectF(
            bg_rect.x() + self.width() * 0.006,
            bg_rect.y() + self.height() * 0.010,
            bg_rect.width(),
            bg_rect.height()
        )
        painter.drawRoundedRect(mid_shadow_rect, corner_radius, corner_radius)
        
        # ====================================================================
        # LAYER 3: Inner shadow (sharp, close to surface) - DARKEST
        # ====================================================================
        painter.setBrush(QBrush(QColor(0, 0, 0, 80)))  # Darkest shadow
        inner_shadow_rect = QRectF(
            bg_rect.x() + self.width() * 0.003,
            bg_rect.y() + self.height() * 0.005,
            bg_rect.width(),
            bg_rect.height()
        )
        painter.drawRoundedRect(inner_shadow_rect, corner_radius, corner_radius)
        
        # ====================================================================
        # MAIN SURFACE: Rich colorful glassmorphism gradient
        # ====================================================================
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        # Vibrant colors with good saturation
        gradient.setColorAt(0.0, QColor(180, 210, 255, 120))  # Rich blue
        gradient.setColorAt(0.35, QColor(200, 180, 255, 115))  # Purple
        gradient.setColorAt(0.65, QColor(255, 190, 230, 115))  # Pink
        gradient.setColorAt(1.0, QColor(255, 220, 200, 120))   # Peachy
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bg_rect, corner_radius, corner_radius)
        
        # ====================================================================
        # BORDER: Subtle white border for definition
        # ====================================================================
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1.5))  # Semi-transparent white
        painter.drawRoundedRect(bg_rect, corner_radius, corner_radius)

    def _draw_neon_border(self, painter):
        """Skip border - modern design doesn't need it with proper shadow"""
        pass  # Border removed for cleaner look

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
        bar_width = total_width * 0.01  # 1% of waveform width
        spacing = total_width * 0.006  # 0.6% of waveform width

        # Calculate total space needed and center the bars
        total_bars_width = (bar_width + spacing) * num_bars
        start_x = waveform_rect.left() + (total_width - total_bars_width) / 2

        # Modern waveform with sophisticated gradient
        painter.setPen(Qt.PenStyle.NoPen)  # No outline

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
            min_height = waveform_rect.height() * 0.02  # 2% minimum height
            max_height = waveform_rect.height() * 0.45  # Half height for symmetry

            # Combine factors
            height_factor = base_height * wave_pattern * random_factor

            # Gentle breathing effect
            breath = 0.9 + (math.sin(self.phase * 2.0 + i * 0.05) * 0.1)
            height_factor *= breath

            # Ensure within bounds
            height_factor = max(0.02, min(1.0, height_factor))

            half_amplitude = min_height + (max_height - min_height) * height_factor

            # Add STRONG audio level influence for dramatic response
            half_amplitude = half_amplitude * (0.3 + level * 0.7)  # 70% influenced by sound

            # Ensure minimum visibility
            half_amplitude = max(min_height, min(half_amplitude, max_height))

            # Calculate opacity based on distance from center for sophistication
            center_position = num_bars / 2
            distance_ratio = abs(i - center_position) / center_position
            
            # Elegant opacity gradient from center to edges
            bar_opacity = int(255 * (1.0 - distance_ratio * 0.4))  # 100% center to 60% edges
            
            # Create gradient for each bar
            bar_gradient = QLinearGradient(x, center_y - half_amplitude, x, center_y + half_amplitude)
            bar_gradient.setColorAt(0.0, QColor(0, 0, 0, bar_opacity))
            bar_gradient.setColorAt(0.5, QColor(20, 20, 20, bar_opacity))  # Slightly lighter center
            bar_gradient.setColorAt(1.0, QColor(0, 0, 0, bar_opacity))
            
            # Draw shadow first for depth
            shadow_rect = QRectF(
                x + 1,  # Slight offset
                center_y - half_amplitude + 1,
                bar_width,
                half_amplitude * 2
            )
            shadow_gradient = QLinearGradient(x, center_y - half_amplitude, x, center_y + half_amplitude)
            shadow_gradient.setColorAt(0.0, QColor(0, 0, 0, 20))
            shadow_gradient.setColorAt(0.5, QColor(0, 0, 0, 40))
            shadow_gradient.setColorAt(1.0, QColor(0, 0, 0, 20))
            painter.fillRect(shadow_rect, QBrush(shadow_gradient))
            
            # Draw main bar on top
            full_bar_rect = QRectF(
                x,
                center_y - half_amplitude,
                bar_width,
                half_amplitude * 2
            )
            painter.fillRect(full_bar_rect, QBrush(bar_gradient))





    def _draw_microphone_icon(self, painter, content_rect):
        """Draw microphone icon at bottom center of popup"""
        # Icon position using ratios (90% from top)
        icon_x = content_rect.center().x()
        icon_y = content_rect.y() + content_rect.height() * 0.9

        # Draw microphone shape - scale based on window size
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Icon size based on content rect dimensions
        icon_size = content_rect.height() * 0.05  # 5% of content height
        
        # Subtle glow using ratios
        for i in range(2):  # Reduced glow layers for cleaner look
            alpha = 40 - i * 20
            glow_size = icon_size * (1 + i * 0.15)  # 15% size increase per layer
            painter.setPen(QPen(QColor(100, 80, 120, alpha), 1))  # Purple tint to match particles
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            
            # Microphone body (rounded rectangle)
            mic_rect = QRectF(
                icon_x - glow_size/2, 
                icon_y - glow_size, 
                glow_size, 
                glow_size * 1.5
            )
            painter.drawRoundedRect(mic_rect, glow_size/2, glow_size/2)

        # Main microphone icon with ratio-based sizing
        icon_size = content_rect.height() * 0.05
        painter.setPen(QPen(QColor(80, 80, 80, 180), 1.5))  # Dark gray to match waveform
        painter.setBrush(QBrush(QColor(80, 80, 80, 80)))
        
        # Microphone body
        mic_width = icon_size * 0.7
        mic_height = icon_size * 1.0
        mic_rect = QRectF(
            icon_x - mic_width/2, 
            icon_y - mic_height, 
            mic_width, 
            mic_height
        )
        painter.drawRoundedRect(mic_rect, mic_width/2, mic_width/2)
        
        # Microphone stand
        painter.setPen(QPen(QColor(80, 80, 80, 180), 1.5))
        stand_height = icon_size * 0.3
        painter.drawLine(
            QPointF(icon_x, icon_y), 
            QPointF(icon_x, icon_y + stand_height)
        )
        
        # Microphone base
        base_width = icon_size * 0.8
        painter.drawLine(
            QPointF(icon_x - base_width/2, icon_y + stand_height), 
            QPointF(icon_x + base_width/2, icon_y + stand_height)
        )
        
        # Microphone arc (sound capture area)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        arc_size = icon_size * 1.2
        arc_rect = QRectF(
            icon_x - arc_size/2, 
            icon_y - mic_height * 0.7, 
            arc_size, 
            arc_size
        )
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
        Internal method to update audio level with enhanced dynamics
        
        Applies exponential scaling to make waveform more reactive to sound:
        - Low levels (whisper): Subtle movement
        - Mid levels (normal speech): Clear waves
        - High levels (loud): Dramatic peaks
        
        Args:
            level: Audio level (0.0 to 1.0)
        """
        with self.level_lock:
            # Clamp to valid range
            raw_level = max(0.0, min(1.0, level))
            
            # Apply aggressive exponential curve for DRAMATIC visual response
            # Power 0.4 = much more amplification of mid-range sounds
            enhanced_level = pow(raw_level, 0.4) * 1.5  # Amplify by 1.5x
            enhanced_level = min(1.0, enhanced_level)  # Clamp to max
            
            # Minimal smoothing to keep it snappy and reactive
            if hasattr(self, '_prev_level'):
                smoothing = 0.15  # Only 15% smoothing = very reactive
                enhanced_level = self._prev_level * smoothing + enhanced_level * (1 - smoothing)
            
            self._prev_level = enhanced_level
            self.current_level = enhanced_level
            
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

# Test code for standalone execution
if __name__ == "__main__":
    """Test the recording popup independently"""
    import sys
    
    app = QApplication(sys.argv)
    
    # Create and show the popup
    popup = RecordingPopup()
    popup.show()
    
    # Start a timer to hide after 10 seconds
    hide_timer = QTimer()
    hide_timer.timeout.connect(lambda: (popup.hide(), app.quit()))
    hide_timer.start(10000)  # 10 seconds
    
    print("🎤 Showing recording popup for 10 seconds...")
    print("   The popup should display with:")
    print("   - Gradient background")
    print("   - Animated waveform")
    print("   - Blurred particle layers")
    print("   - Timer display")
    
    sys.exit(app.exec())
