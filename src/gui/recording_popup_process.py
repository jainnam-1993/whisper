#!/usr/bin/env python3
"""Process wrapper for PyQt6 recording popup to run with its own event loop."""

import multiprocessing
from multiprocessing import Queue
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PopupProcess:
    """Manages the recording popup in a separate process with its own Qt event loop."""

    def __init__(self):
        self.process: Optional[multiprocessing.Process] = None
        self.command_queue: Optional[Queue] = None
        self.response_queue: Optional[Queue] = None
        self._started = False

    def start(self):
        """Start the popup process with Qt event loop."""
        if self._started:
            logger.warning("Popup process already started")
            return

        self.command_queue = Queue()
        self.response_queue = Queue()

        self.process = multiprocessing.Process(
            target=self._run_popup_process,
            args=(self.command_queue, self.response_queue),
            daemon=True
        )
        self.process.start()
        self._started = True
        logger.info("Popup process started")

    def _run_popup_process(self, cmd_queue: Queue, resp_queue: Queue):
        """Run the Qt application in a separate process."""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            from src.gui.recording_popup import RecordingPopupManager

            app = QApplication(sys.argv)
            manager = RecordingPopupManager()

            def check_commands():
                """Check for commands from main process."""
                try:
                    while not cmd_queue.empty():
                        cmd = cmd_queue.get_nowait()

                        if cmd == "show":
                            manager.show_recording_popup()
                            resp_queue.put("shown")

                        elif cmd == "hide":
                            manager.hide_recording_popup()
                            resp_queue.put("hidden")

                        elif cmd == "quit":
                            app.quit()
                            return

                except Exception as e:
                    logger.error(f"Error processing command: {e}")

                # Schedule next check
                QTimer.singleShot(50, check_commands)  # Check every 50ms

            # Start checking for commands
            check_commands()

            # Run Qt event loop
            app.exec()

        except Exception as e:
            logger.error(f"Error in popup process: {e}")
            resp_queue.put(f"error: {e}")

    def show(self):
        """Show the recording popup."""
        if not self._started:
            self.start()

        if self.command_queue:
            self.command_queue.put("show")
            logger.debug("Sent show command to popup process")

    def hide(self):
        """Hide the recording popup."""
        if not self._started:
            logger.warning("Cannot hide popup - process not started")
            return

        if self.command_queue:
            self.command_queue.put("hide")
            logger.debug("Sent hide command to popup process")

    def stop(self):
        """Stop the popup process."""
        if not self._started:
            return

        if self.command_queue:
            self.command_queue.put("quit")

        if self.process and self.process.is_alive():
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=1)

        self._started = False
        logger.info("Popup process stopped")


# Global instance for the popup process
_popup_process: Optional[PopupProcess] = None


def get_popup_process() -> PopupProcess:
    """Get or create the global popup process instance."""
    global _popup_process
    if _popup_process is None:
        _popup_process = PopupProcess()
        _popup_process.start()
    return _popup_process


def show_recording_popup():
    """Show the recording popup (for compatibility with existing code)."""
    try:
        popup = get_popup_process()
        popup.show()
    except Exception as e:
        logger.warning(f"Could not show recording popup: {e}")


def hide_recording_popup():
    """Hide the recording popup (for compatibility with existing code)."""
    try:
        popup = get_popup_process()
        popup.hide()
    except Exception as e:
        logger.warning(f"Could not hide recording popup: {e}")


def cleanup_popup_process():
    """Clean up the popup process on application exit."""
    global _popup_process
    if _popup_process:
        _popup_process.stop()
        _popup_process = None