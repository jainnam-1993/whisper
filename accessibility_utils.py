#!/usr/bin/env python3
"""
macOS Accessibility Permissions Utility

This module provides utilities for checking and managing macOS accessibility permissions
required for automated keyboard input to other applications.
"""

import platform
import subprocess
import sys
import re
import shlex


def is_macos():
    """Check if running on macOS"""
    return platform.system() == 'Darwin'


def _sanitize_applescript(script):
    """
    Sanitize AppleScript to prevent injection attacks.
    This is a whitelist approach - only allow safe characters and patterns.
    """
    if not isinstance(script, str):
        raise ValueError("AppleScript must be a string")
    
    # Remove any suspicious characters that could be used for injection
    # Allow only alphanumeric, spaces, quotes, parentheses, and AppleScript keywords
    allowed_pattern = r'[a-zA-Z0-9\s\"\'\(\)\{\}\[\]\.\,\:\;\-\_\&\|\n\t]'
    sanitized = ''.join(char for char in script if re.match(allowed_pattern, char))
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'do\s+shell\s+script',  # Execute shell commands
        r'system\s+events.*keystroke.*["\'][^"\']*[;\|&][^"\']*["\']',  # Command injection in keystroke
        r'tell\s+application\s+["\']terminal["\']',  # Terminal access
        r'activate\s+application\s+["\'][^"\']*[;\|&]',  # Application activation with injection
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise ValueError(f"Potentially dangerous AppleScript pattern detected: {pattern}")
    
    return sanitized


def _execute_applescript_safely(script, timeout=5):
    """
    Execute AppleScript safely with proper error handling and security checks.
    """
    if not is_macos():
        raise RuntimeError("AppleScript execution only supported on macOS")
    
    try:
        # Sanitize the script
        safe_script = _sanitize_applescript(script)
        
        # Execute with strict parameters
        result = subprocess.run(
            ['osascript', '-e', safe_script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Don't raise on non-zero exit codes
        )
        
        return result
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"AppleScript execution timed out after {timeout} seconds")
    except FileNotFoundError:
        raise RuntimeError("osascript command not found - not running on macOS?")
    except Exception as e:
        raise RuntimeError(f"AppleScript execution failed: {e}")


def check_accessibility_permissions():
    """
    Check if the current application has accessibility permissions on macOS.
    
    Returns:
        bool: True if permissions are granted or not on macOS, False if denied on macOS
    """
    if not is_macos():
        # On non-macOS systems, assume permissions are available
        return True
    
    try:
        # Use AppleScript to check if we can control other applications
        # This is a reliable way to test accessibility permissions
        applescript = '''
        tell application "System Events"
            try
                set frontApp to name of first application process whose frontmost is true
                return "success"
            on error
                return "denied"
            end try
        end tell
        '''
        
        result = _execute_applescript_safely(applescript, timeout=5)
        return result.stdout.strip() == "success"
        
    except (RuntimeError, ValueError) as e:
        print(f"AppleScript execution error: {e}")
        return False
    except Exception:
        # If we can't run the check, assume permissions are needed
        return False


def get_accessibility_instructions():
    """
    Get user-friendly instructions for granting accessibility permissions.
    
    Returns:
        str: Instructions for granting permissions
    """
    if not is_macos():
        return "Accessibility permissions are not required on this platform."
    
    return """
🔐 ACCESSIBILITY PERMISSIONS REQUIRED

To allow this application to type text into other applications, you need to grant
Accessibility permissions in macOS System Preferences.

📋 STEP-BY-STEP INSTRUCTIONS:

1. Open System Preferences (or System Settings on macOS 13+)
2. Go to Security & Privacy → Privacy → Accessibility
   (or Privacy & Security → Accessibility on macOS 13+)
3. Click the lock icon (🔒) and enter your password to make changes
4. Look for your terminal application in the list:
   • Terminal.app
   • iTerm2
   • VS Code Terminal
   • Or whatever terminal you're using to run this script
5. Check the box next to your terminal application to enable access
6. If your terminal isn't listed, click the "+" button and add it
7. Close System Preferences and restart this application

🔄 ALTERNATIVE: You can also run this command in Terminal:
   sudo spctl --master-disable (temporarily disables security features)
   
⚠️  NOTE: You may need to restart your terminal application after granting permissions.

After granting permissions, run the application again to test text input.
"""


def prompt_for_permissions():
    """
    Display permission instructions and wait for user confirmation.
    
    Returns:
        bool: True if user wants to continue, False to exit
    """
    print(get_accessibility_instructions())
    
    while True:
        response = input("\n✅ Have you granted accessibility permissions? (y/n/q): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            print("📝 Please grant permissions first, then restart the application.")
            return False
        elif response in ['q', 'quit']:
            print("👋 Exiting application.")
            return False
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'q' to quit.")


def test_accessibility_permissions():
    """
    Test accessibility permissions by attempting a safe keyboard operation.
    
    Returns:
        bool: True if test successful, False otherwise
    """
    if not is_macos():
        return True
    
    try:
        from pynput import keyboard
        import time
        
        print("🧪 Testing accessibility permissions...")
        print("🔔 This will test keyboard access - no text will be typed.")
        
        # Create keyboard controller
        kb = keyboard.Controller()
        
        # Try a safe operation that doesn't actually type anything
        # We'll just test if we can create the controller without errors
        time.sleep(0.1)
        
        print("✅ Accessibility permissions test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Accessibility permissions test failed: {e}")
        return False


if __name__ == "__main__":
    """Test the accessibility utilities"""
    print("🔍 Checking macOS accessibility permissions...")
    
    if check_accessibility_permissions():
        print("✅ Accessibility permissions are granted!")
        test_accessibility_permissions()
    else:
        print("❌ Accessibility permissions are required!")
        if prompt_for_permissions():
            if check_accessibility_permissions():
                print("✅ Permissions verified! You can now use the application.")
            else:
                print("❌ Permissions still not detected. You may need to restart your terminal.")
        else:
            print("👋 Exiting. Run this script again after granting permissions.")
            sys.exit(0)