"""
LearnBase Notification Host Listener

Lightweight HTTP server that receives notification requests from the Docker
container and triggers macOS desktop notifications via terminal-notifier
or osascript fallback.

Runs on localhost:19876. Writes PID to /tmp/learnbase-notify-listener.pid.
"""

import json
import logging
import os
import signal
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("notify-listener")

HOST = "127.0.0.1"
PORT = 19876
PID_FILE = "/tmp/learnbase-notify-listener.pid"

def send_macos_notification(title: str, subtitle: str, message: str):
    """Send a macOS desktop notification via osascript."""
    display_text = f"{subtitle} — {message}" if subtitle else message
    # Escape double quotes for AppleScript string
    escaped_text = display_text.replace('"', '\\"')
    escaped_title = title.replace('"', '\\"')

    cmd = [
        "osascript", "-e",
        f'display alert "{escaped_title}" message "{escaped_text}" giving up after 30',
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=35)
        log.info("Notification delivered: %s — %s", subtitle, message)
    except subprocess.CalledProcessError as e:
        log.error("Notification command failed: %s", e.stderr.decode().strip())
    except subprocess.TimeoutExpired:
        log.error("Notification command timed out")


class NotificationHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        title = payload.get("title", "LearnBase")
        subtitle = payload.get("subtitle", "")
        message = payload.get("message", "")

        send_macos_notification(title, subtitle, message)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        # Suppress default request logging, we handle our own
        pass


def write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    log.info("PID %d written to %s", os.getpid(), PID_FILE)


def remove_pid():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def handle_signal(signum, frame):
    log.info("Received %s, shutting down...", signal.Signals(signum).name)
    remove_pid()
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    write_pid()

    log.info("Starting listener on %s:%d using osascript", HOST, PORT)

    server = HTTPServer((HOST, PORT), NotificationHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        remove_pid()
        log.info("Listener stopped.")


if __name__ == "__main__":
    main()
