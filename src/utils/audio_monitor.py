"""
Real-time Audio Level Monitor for Recording Popup
Captures microphone input and calculates audio levels for waveform visualization
"""

import threading
import time
import numpy as np
from typing import Optional, Callable
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("⚠️ PyAudio not available - audio level monitoring disabled")


class AudioLevelMonitor:
    """
    Monitors microphone input and provides real-time audio level data
    for waveform visualization in the recording popup
    """
    
    def __init__(self, callback: Optional[Callable[[float], None]] = None):
        """
        Initialize audio level monitor
        
        Args:
            callback: Function to call with audio levels (0.0 to 1.0)
        """
        self.callback = callback
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # PyAudio configuration
        self.chunk = 1024  # Number of frames per buffer
        self.sample_rate = 44100  # Sample rate
        self.channels = 1  # Mono
        self.format = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
        
        self.audio = None
        self.stream = None
        
        # Level calculation
        self.rms_window = []
        self.window_size = 5  # Average over 5 samples for smoother levels
    
    def start_monitoring(self):
        """Start monitoring audio levels"""
        if not PYAUDIO_AVAILABLE:
            print("⚠️ Cannot start audio monitoring - PyAudio not available")
            return False
            
        if self.is_monitoring:
            return True
            
        try:
            self.is_monitoring = True
            self.audio = pyaudio.PyAudio()
            
            # Open microphone stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk,
                stream_callback=None  # We'll use read() for synchronous access
            )
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            print("🎤 Audio level monitoring started")
            return True
            
        except Exception as e:
            print(f"❌ Error starting audio monitoring: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self):
        """Stop monitoring audio levels"""
        self.is_monitoring = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
            
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
            self.audio = None
            
        # Wait for monitor thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=0.5)
        
        print("🔇 Audio level monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in background thread"""
        while self.is_monitoring and self.stream:
            try:
                # Read audio data
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                
                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS (Root Mean Square) for audio level
                rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))
                
                # Normalize to 0.0 - 1.0 range
                # 32767 is max value for int16
                normalized_level = min(1.0, rms / 8000.0)  # Adjust divisor for sensitivity
                
                # Apply smoothing window
                self.rms_window.append(normalized_level)
                if len(self.rms_window) > self.window_size:
                    self.rms_window.pop(0)
                
                # Calculate smoothed average
                smoothed_level = sum(self.rms_window) / len(self.rms_window)
                
                # Call callback with level
                if self.callback:
                    self.callback(smoothed_level)
                
                # Small delay to prevent overwhelming the callback
                time.sleep(0.02)  # ~50 updates per second
                
            except Exception as e:
                if self.is_monitoring:  # Only log if we're still supposed to be monitoring
                    print(f"Audio monitoring error: {e}")
                break
    
    def get_available_devices(self):
        """Get list of available audio input devices"""
        if not PYAUDIO_AVAILABLE:
            return []
            
        devices = []
        try:
            audio = pyaudio.PyAudio()
            
            for i in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:  # Input device
                    devices.append({
                        'index': i,
                        'name': info['name'],
                        'channels': info['maxInputChannels'],
                        'sample_rate': int(info['defaultSampleRate'])
                    })
            
            audio.terminate()
        except Exception as e:
            print(f"Error getting audio devices: {e}")
            
        return devices


class MockAudioMonitor:
    """
    Mock audio monitor for testing when PyAudio is not available
    Generates fake audio levels for development
    """
    
    def __init__(self, callback: Optional[Callable[[float], None]] = None):
        self.callback = callback
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
    
    def start_monitoring(self):
        """Start generating fake audio levels"""
        if self.is_monitoring:
            return True
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._mock_loop, daemon=True)
        self.monitor_thread.start()
        
        print("🎭 Mock audio level monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop generating fake audio levels"""
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=0.5)
        
        print("🔇 Mock audio monitoring stopped")
    
    def _mock_loop(self):
        """Generate fake audio levels for testing"""
        import random
        import math
        
        frame = 0
        while self.is_monitoring:
            # Generate realistic-looking audio levels
            # Base level with some variation
            base_level = 0.1 + 0.3 * abs(math.sin(frame * 0.1))
            # Add random spikes to simulate speech
            if random.random() < 0.3:  # 30% chance of speech spike
                base_level += random.uniform(0.2, 0.6)
            
            level = min(1.0, base_level)
            
            if self.callback:
                self.callback(level)
            
            frame += 1
            time.sleep(0.05)  # 20 FPS
    
    def get_available_devices(self):
        """Return mock device list"""
        return [{'index': 0, 'name': 'Mock Microphone', 'channels': 1, 'sample_rate': 44100}]


# Factory function to create appropriate monitor
def create_audio_monitor(callback: Optional[Callable[[float], None]] = None) -> 'AudioLevelMonitor':
    """Create audio monitor - real if PyAudio available, mock otherwise"""
    if PYAUDIO_AVAILABLE:
        return AudioLevelMonitor(callback)
    else:
        return MockAudioMonitor(callback)