#!/bin/bash

# Set the working directory
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to check container status
check_container() {
  CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' whisper-dictation 2>/dev/null || echo "not_found")
  HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' whisper-dictation 2>/dev/null || echo "not_found")
  
  echo "Container Status: $CONTAINER_STATUS"
  echo "Health Status: $HEALTH_STATUS"
  
  if [ "$CONTAINER_STATUS" != "running" ]; then
    echo "Container is not running. Attempting to restart..."
    docker-compose up -d
  elif [ "$HEALTH_STATUS" == "unhealthy" ]; then
    echo "Container is unhealthy. Restarting..."
    docker-compose restart
  fi
}

# Main menu
while true; do
  clear
  echo "==========================="
  echo "Whisper Docker Monitor"
  echo "==========================="
  echo "1. Check container status"
  echo "2. View container logs"
  echo "3. Restart container"
  echo "4. Rebuild and restart container"
  echo "5. Exit"
  echo "==========================="
  
  read -p "Select an option: " option
  
  case $option in
    1)
      check_container
      read -p "Press Enter to continue..."
      ;;
    2)
      docker logs whisper-dictation
      read -p "Press Enter to continue..."
      ;;
    3)
      docker-compose restart
      echo "Container restarted"
      read -p "Press Enter to continue..."
      ;;
    4)
      docker-compose up -d --build
      echo "Container rebuilt and restarted"
      read -p "Press Enter to continue..."
      ;;
    5)
      exit 0
      ;;
    *)
      echo "Invalid option"
      read -p "Press Enter to continue..."
      ;;
  esac
done 