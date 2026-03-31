#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="learnbase-notify"
PID_FILE="/tmp/learnbase-notify-listener.pid"

# --- Stop Docker container ---
if docker ps -q -f "name=$CONTAINER_NAME" 2>/dev/null | grep -q .; then
    echo "Stopping notification container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    echo "Container stopped."
else
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    echo "No running notification container found."
fi

# --- Stop host listener ---
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping host listener (PID $PID)..."
        kill "$PID" 2>/dev/null || true
        echo "Listener stopped."
    else
        echo "Listener process (PID $PID) already stopped."
    fi
    rm -f "$PID_FILE"
else
    echo "No listener PID file found."
fi

echo "Notification daemon shut down."
