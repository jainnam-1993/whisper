# Docker Configuration for Whisper

This project now includes Docker support for easier deployment and improved reliability.

## Features

- **Self-healing container**: The Docker container is configured to automatically restart if the application crashes
- **Health monitoring**: Regular health checks ensure the application is running properly
- **Logging**: Container logs are stored with rotation to prevent disk space issues
- **Easy startup**: The existing `startup.sh` script now includes Docker support by default
- **Key listening**: Host-side key listener for double Command key press that works with the Docker container

## Container Architecture

The Docker container runs a headless version of the Whisper service. This is because:

1. The GUI components of the original application (status bar, keyboard interactions) are macOS-specific and won't work in Linux containers
2. The container version focuses on reliability and monitoring

The system works as follows:

1. A host-side Python script (`host_key_listener.py`) runs on your Mac and listens for key presses
2. When you double-press the Right Command key, it starts recording audio
3. When you press Right Command key again, it stops recording and sends the audio to the Docker container
4. The container transcribes the audio using the Whisper model
5. The transcription is returned to the host script which types it out

## Prerequisites

- Docker Desktop installed and running
- Python 3 with pynput package
- Sox audio recording tool (`brew install sox` on macOS)

## Running with Docker

The default startup now uses Docker:

```bash
./startup.sh
```

If you prefer to run without Docker (the old way):

```bash
./startup.sh --no-docker
```

## Using the Dictation Service

With Docker mode (default):
1. Double-press the Right Command key to start recording
2. Speak clearly into your microphone
3. Press Right Command key once to stop recording and process transcription
4. The transcribed text will be typed out automatically

## Container Management

We've included a monitoring tool to help manage the Docker container:

```bash
./docker-monitor.sh
```

This tool provides options to:
- Check container status
- View logs
- Restart the container
- Rebuild and restart the container

## Docker Configuration

The Docker configuration includes:

- **Dockerfile**: Builds the Whisper application environment with all dependencies
- **docker-compose.yml**: Manages the container with restart policies and resource limits
- **docker-startup.sh**: Helper script to ensure Docker is running and start the container

## Troubleshooting

- Check logs in the `logs/` directory for container restart events
- Container logs can be viewed with:
  ```bash
  docker logs whisper-dictation
  ```
- Host-side key listener logs are in `host-listener.log`
- To restart the container:
  ```bash
  docker-compose restart
  ```
- To rebuild and restart (after code changes):
  ```bash
  docker-compose up -d --build
  ``` 