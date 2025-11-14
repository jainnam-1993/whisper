"""
AudioDeviceManager - Dynamic macOS audio input device selection.

Monitors macOS default input device and triggers service restart on changes.

Architecture:
- Singleton pattern for system-wide device management
- Background thread polling every 2 seconds using SwitchAudioSource
- Callback notification system triggers service restart
- Thread-safe device querying

Usage:
    from src.utils.audio_device_manager import AudioDeviceManager

    manager = AudioDeviceManager.get_instance()
    manager.start_monitoring()

    def on_device_change(device_name):
        print(f"Device changed to: {device_name}")
        sys.exit(0)  # Restart service

    manager.register_callback(on_device_change)

Requirements:
    - SwitchAudioSource CLI tool: brew install switchaudio-osx
"""

import threading
import time
import logging
import subprocess
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)


class AudioDeviceManager:
    """
    Manages audio input device monitoring with automatic change detection.

    Singleton pattern ensures system-wide consistency. Polls macOS default
    input device using SwitchAudioSource and notifies callbacks on changes.

    Thread Safety:
        All public methods are thread-safe using internal locking.
    """

    _instance: Optional['AudioDeviceManager'] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize AudioDeviceManager. Use get_instance() instead."""
        self._current_device_name: Optional[str] = None
        self._monitoring = False
        self._callbacks: List[Callable[[str], None]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        logger.info("AudioDeviceManager initialized")

    @classmethod
    def get_instance(cls) -> 'AudioDeviceManager':
        """
        Get or create the singleton instance.

        Returns:
            AudioDeviceManager: The singleton instance

        Thread Safety:
            This method is thread-safe.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_device_name_via_switchaudio(self) -> Optional[str]:
        """
        Get current default input device name using SwitchAudioSource.

        Queries macOS CoreAudio directly, bypassing PortAudio caching.

        Returns:
            Optional[str]: Device name or None on error

        Notes:
            - Requires: brew install switchaudio-osx
            - Not affected by PortAudio initialization locks
        """
        try:
            result = subprocess.run(
                ['SwitchAudioSource', '-t', 'input', '-c'],
                capture_output=True,
                text=True,
                timeout=1.0
            )
            if result.returncode == 0:
                device_name = result.stdout.strip()
                if device_name:
                    return device_name
        except FileNotFoundError:
            logger.warning("SwitchAudioSource not found (install: brew install switchaudio-osx)")
            return None
        except Exception as e:
            logger.error(f"Error running SwitchAudioSource: {e}")
            return None

        return None

    def get_default_input_device(self) -> Optional[str]:
        """
        Query the current macOS default input device name.

        Returns:
            Optional[str]: Device name or None on error

        Thread Safety:
            This method is thread-safe.
        """
        try:
            device_name = self._get_device_name_via_switchaudio()

            # Cache the result
            with self._lock:
                self._current_device_name = device_name

            return device_name

        except Exception as e:
            logger.error(f"Error querying default input device: {e}")

            # Return cached value if query fails
            with self._lock:
                return self._current_device_name

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback for device changes.

        Args:
            callback: Function called when device changes.
                Signature: callback(device_name: str)

        Thread Safety:
            This method is thread-safe.

        Notes:
            - Callback invoked from background thread
            - Should be fast and non-blocking
        """
        with self._lock:
            self._callbacks.append(callback)
        logger.debug("Registered device change callback")

    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """
        Remove a registered callback.

        Args:
            callback: The callback function to remove

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.debug("Removed device change callback")

    def start_monitoring(self, poll_interval: float = 2.0) -> None:
        """
        Start background monitoring for device changes.

        Args:
            poll_interval: Seconds between polls (default: 2.0)

        Thread Safety:
            This method is thread-safe.

        Raises:
            RuntimeError: If SwitchAudioSource not available
        """
        with self._lock:
            if self._monitoring:
                logger.warning("Device monitoring already active")
                return

            self._monitoring = True
            self._stop_event.clear()

        # Query initial device
        device_name = self.get_default_input_device()
        if device_name is None:
            raise RuntimeError("Cannot start monitoring: SwitchAudioSource unavailable")

        logger.info(f"Starting device monitoring with initial device: {device_name}")

        # Start background thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(poll_interval,),
            daemon=True,
            name="AudioDeviceMonitor"
        )
        self._monitor_thread.start()
        logger.info(f"Device monitoring started (poll interval: {poll_interval}s)")

    def stop_monitoring(self) -> None:
        """
        Stop background monitoring.

        Thread Safety:
            This method is thread-safe.
        """
        with self._lock:
            if not self._monitoring:
                return

            self._monitoring = False
            self._stop_event.set()

        # Wait for thread to exit
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        self._monitor_thread = None

    def _monitor_loop(self, poll_interval: float) -> None:
        """
        Background monitoring loop (runs in separate thread).

        Args:
            poll_interval: Seconds between device polls
        """
        logger.debug(f"Device monitoring loop started (polling every {poll_interval}s)")

        while not self._stop_event.is_set():
            try:
                # Read previous device name BEFORE querying
                with self._lock:
                    previous_name = self._current_device_name
                    current_callbacks = list(self._callbacks)

                # Query current device
                device_name = self.get_default_input_device()

                # Device changed?
                if device_name != previous_name and device_name is not None:
                    logger.info(f"Device changed: {previous_name} → {device_name}")

                    # Notify callbacks
                    for callback in current_callbacks:
                        try:
                            callback(device_name)
                        except Exception as e:
                            logger.error(f"Error in device change callback: {e}")

                # Sleep until next poll
                self._stop_event.wait(timeout=poll_interval)

            except Exception as e:
                logger.error(f"Error in device monitoring loop: {e}")
                self._stop_event.wait(timeout=poll_interval)

        logger.debug("Device monitoring loop exited")

    def cleanup(self) -> None:
        """
        Cleanup resources and stop monitoring.

        Thread Safety:
            This method is thread-safe.
        """
        logger.info("Cleaning up AudioDeviceManager")

        # Stop monitoring
        self.stop_monitoring()

        # Clear callbacks
        with self._lock:
            self._callbacks.clear()

        logger.info("AudioDeviceManager cleanup complete")


def cleanup_device_manager() -> None:
    """
    Global cleanup function for application shutdown.

    Register with atexit:
        import atexit
        atexit.register(cleanup_device_manager)
    """
    instance = AudioDeviceManager.get_instance()
    instance.cleanup()
