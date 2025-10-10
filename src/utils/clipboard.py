#!/usr/bin/env python3
"""
Unified Clipboard Manager for Whisper Dictation
Consolidates all clipboard handling with robust error handling and multiple fallback methods
"""

import subprocess
import time
import traceback
from typing import Optional
from .accessibility import _execute_applescript_safely


class ClipboardManager:
    """
    Unified clipboard manager with robust error handling and multiple paste methods.
    
    Features:
    - Clipboard preservation and restoration
    - Multi-tier paste fallback system
    - Text sanitization and validation
    - macOS-optimized with pbcopy/pbpaste integration
    - AppleScript and keyboard simulation fallbacks
    """
    
    def __init__(self):
        self.preserved_content: Optional[str] = None
    
    def preserve_clipboard(self) -> bool:
        """
        Preserve current clipboard content using pbpaste (macOS optimized)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
            self.preserved_content = result.stdout
            print(f"Preserved clipboard content ({len(self.preserved_content)} chars)")
            return True
        except Exception as e:
            print(f"Warning: Could not preserve clipboard: {e}")
            self.preserved_content = None
            return False
    
    def restore_clipboard(self) -> bool:
        """
        Restore previously preserved clipboard content
        
        Returns:
            bool: True if successful, False otherwise
        """
        if self.preserved_content is not None:
            try:
                process = subprocess.Popen(
                    ['pbcopy'],
                    stdin=subprocess.PIPE,
                    close_fds=True
                )
                process.communicate(input=self.preserved_content.encode('utf-8'))
                print(f"✓ Restored original clipboard content ({len(self.preserved_content)} chars)")
                return True
            except Exception as e:
                print(f"Warning: Could not restore clipboard: {e}")
                return False
        else:
            print("No preserved clipboard content to restore")
            return False
    
    def copy_to_clipboard(self, text: str) -> bool:
        """
        Copy text to clipboard with verification and retries
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not text:
            return False
            
        # Sanitize text to prevent clipboard issues
        text = text.strip()
        # Remove any null bytes or other problematic characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        if not text:
            print("No valid text after sanitization")
            return False
        
        try:
            # Use pbcopy - simple and direct, no retries needed
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                close_fds=True
            )
            process.communicate(input=text.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
            traceback.print_exc()
            return False
    
    def paste_from_clipboard_applescript(self) -> bool:
        """
        Paste using AppleScript - most reliable on macOS
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Attempting to paste with AppleScript...")
            # Create AppleScript to paste content from clipboard
            applescript = '''
            try
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    log "Current frontmost app: " & frontApp
                    keystroke "v" using command down
                    return "success"
                end tell
            on error errMsg
                log "Error in AppleScript: " & errMsg
                return "error: " & errMsg
            end try
            '''

            # Execute the AppleScript securely
            result = _execute_applescript_safely(applescript, timeout=5)
            print(f"AppleScript result: stdout={result.stdout.strip()}, stderr={result.stderr.strip()}")

            if result.returncode == 0 and "error:" not in result.stdout:
                print("AppleScript paste seems successful")
                return True
            else:
                print(f"AppleScript paste failed: {result.stderr or result.stdout}")
                return False
        except (RuntimeError, ValueError) as e:
            print(f"Secure AppleScript execution failed: {e}")
            return False
        except Exception as e:
            print(f"Error pasting with AppleScript: {e}")
            traceback.print_exc()
            return False
    
    def paste_from_clipboard_keyboard(self) -> bool:
        """
        Paste using keyboard simulation as fallback
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from pynput import keyboard
            keyboard_controller = keyboard.Controller()
            with keyboard_controller.pressed(keyboard.Key.cmd):
                keyboard_controller.press('v')
                keyboard_controller.release('v')
            return True
        except Exception as e:
            print(f"Error pasting from clipboard: {e}")
            traceback.print_exc()
            return False
    
    def paste_from_clipboard(self) -> bool:
        """
        Paste from clipboard with multiple fallback methods
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Try AppleScript first (most reliable)
        if self.paste_from_clipboard_applescript():
            return True
        
        # Fallback to keyboard simulation
        return self.paste_from_clipboard_keyboard()
    
    def copy_and_paste_text(self, text: str) -> bool:
        """
        Complete workflow: preserve → copy → paste → restore
        
        Args:
            text: Text to copy and paste
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not text or not text.strip():
            print("No text to copy and paste")
            return False
        
        # Preserve current clipboard
        self.preserve_clipboard()
        
        try:
            # Copy text to clipboard
            if not self.copy_to_clipboard(text):
                print("Failed to copy text to clipboard")
                return False
            
            print("Text copied to clipboard")
            time.sleep(0.5)  # Allow clipboard to settle
            
            # Paste from clipboard
            if self.paste_from_clipboard():
                print("Text pasted successfully")
                time.sleep(0.5)  # Allow paste to complete
                self.restore_clipboard()
                return True
            else:
                print("Failed to paste - please paste manually (Cmd+V)")
                return False
                
        except Exception as e:
            print(f"Error in copy_and_paste_text: {e}")
            return False
        finally:
            # Always try to restore clipboard
            if not hasattr(self, '_restored'):
                self.restore_clipboard()


class TranscriptionHandler:
    """
    Single responsibility class for handling ALL transcription pasting.
    Eliminates duplicate paste operations by centralizing the workflow.
    """
    
    def __init__(self, clipboard_manager: ClipboardManager):
        self.clipboard = clipboard_manager
        
        # Initialize text enhancement service
        from ..services.text_enhancement_service import get_text_enhancement_service
        self.text_enhancer = get_text_enhancement_service()
    
    def handle_transcription(self, text: str, source: str) -> bool:
        """
        Single point for ALL transcription pasting - no duplicates.
        Applies text enhancement before pasting.
        
        Args:
            text: Transcribed text to paste
            source: Source identifier for logging (manual_stop/manual_background)
            
        Returns:
            bool: True if pasted successfully, False otherwise
        """
        if not text or not text.strip():
            print(f"⚠️ No text to paste from {source}")
            return False
            
        text = text.strip()
        
        print(f"📝 Processing transcription from {source}: '{text}'")
        
        # Apply text enhancement (capitalization, punctuation, grammar)
        enhanced_text = self.text_enhancer.enhance(text)
        
        if enhanced_text != text:
            print(f"✨ Enhanced: '{enhanced_text}'")
        
        success = self.clipboard.copy_and_paste_text(enhanced_text)
        
        if success:
            print(f"✅ Text successfully pasted from {source}")
        else:
            print(f"❌ Failed to paste text from {source}")
            
        return success


# Legacy compatibility - keep existing imports working
def create_clipboard_manager() -> ClipboardManager:
    """Factory function for creating clipboard manager instances"""
    return ClipboardManager()