#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_PATH="${1:-$HOME/.learnbase/daily/notify-config.json}"
CONTAINER_NAME="learnbase-notify"
IMAGE_NAME="learnbase-notify:latest"
PID_FILE="/tmp/learnbase-notify-listener.pid"
LISTENER_SCRIPT="$SCRIPT_DIR/notify-host-listener.py"

# --- Validate config ---
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Error: Config file not found: $CONFIG_PATH"
    exit 1
fi

if ! python3 -m json.tool "$CONFIG_PATH" > /dev/null 2>&1; then
    echo "Error: Invalid JSON in config file: $CONFIG_PATH"
    exit 1
fi

echo "Config: $CONFIG_PATH"

# --- Check Docker is available ---
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Start Docker Desktop and try again."
    echo "See docs/docker-setup-guide.md for setup instructions."
    exit 1
fi

# --- Check image exists ---
if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${IMAGE_NAME}$"; then
    echo "Error: Docker image '$IMAGE_NAME' not found."
    echo "Build it first: docker build -t $IMAGE_NAME $PROJECT_DIR/docker/"
    exit 1
fi

# --- Clean up existing processes ---

# Stop existing host listener
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing listener (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# Remove existing container
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# --- Start host listener ---
echo "Starting host listener..."
python3 "$LISTENER_SCRIPT" &
LISTENER_PID=$!

# Wait briefly and verify it started
sleep 1
if ! kill -0 "$LISTENER_PID" 2>/dev/null; then
    echo "Error: Host listener failed to start. Check port 19876 is available."
    exit 1
fi
echo "Host listener running (PID $LISTENER_PID)"

# --- Start Docker container ---
echo "Starting notification container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$CONFIG_PATH":/config/notify-config.json:ro \
    "$IMAGE_NAME"

echo ""
echo "Notifications active. Events scheduled:"
python3 -c "
import json, sys
with open('$CONFIG_PATH') as f:
    config = json.load(f)
for n in config.get('notifications', []):
    times = ', '.join(t.split('T')[1][:5] for t in n.get('notify_at', []))
    print(f\"  {n.get('event', '?')} — notify at {times}\")
"
echo ""
echo "View daemon logs: docker logs -f $CONTAINER_NAME"
