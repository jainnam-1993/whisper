#!/bin/bash

# Set the working directory
cd "$(dirname "$0")"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running. Starting Docker..."
  open -a Docker
  # Wait for Docker to start
  while ! docker info > /dev/null 2>&1; do
    sleep 5
  done
  echo "Docker is now running"
fi

# Build and start Docker container
echo "Starting Whisper in Docker container..."
docker-compose up -d --build

# Log startup info
echo "$(date): Whisper Docker container started" >> logs/docker-startup.log

# Setup monitoring for container restarts
docker events --filter 'container=whisper-dictation' --filter 'event=restart' | while read event
do
    echo "$(date): Container restarted due to error - $event" >> logs/docker-restart.log
done & 