#!/bin/bash

# Function to handle the double command press
handle_double_press() {
    # Add your desired action here
    osascript -e 'display notification "Double Command pressed!"'
    # You can add more commands here
}

# Variables for tracking command key state
last_press=0
threshold=0.3  # seconds between presses to count as double-press

# Monitor for command key events
while true; do
    # Check if left or right command key is pressed
    if osascript -e 'tell application "System Events" to key code 55 or key code 54'; then
        current_time=$(date +%s.%N)
        time_diff=$(echo "$current_time - $last_press" | bc)
        if (( $(echo "$time_diff < $threshold" | bc -l) )); then
            handle_double_press
        fi
        last_press=$current_time
        sleep 0.1
    fi
    sleep 0.05
done
