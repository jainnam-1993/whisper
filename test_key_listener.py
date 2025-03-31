#!/usr/bin/env python3
import time
from pynput import keyboard

def on_press(key):
    try:
        print(f'Key pressed: {key.char}')
    except AttributeError:
        print(f'Special key pressed: {key}')
        
    # Check if right command key was pressed
    if key == keyboard.Key.cmd_r:
        print("Right Command key detected!")

def on_release(key):
    print(f'Key released: {key}')
    if key == keyboard.Key.esc:
        # Stop listener
        return False

# Start listener
print("Key listener test started. Press keys to see them detected.")
print("Press Right Command key to see if it's detected correctly.")
print("Press ESC to exit.")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join() 