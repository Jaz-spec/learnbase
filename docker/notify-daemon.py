"""
LearnBase Calendar Notification Daemon

Runs inside a Docker container. Reads a JSON config of scheduled notifications,
sleeps until each notification time, and sends HTTP POST to the host-side listener
which triggers macOS desktop notifications.

Config is mounted at /config/notify-config.json.
Host listener runs at host.docker.internal:19876.
"""

import json
import logging
import signal
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("notify-daemon")

CONFIG_PATH = Path("/config/notify-config.json")
HOST_LISTENER_URL = "http://host.docker.internal:19876/notify"

stop_event = threading.Event()


def handle_signal(signum, frame):
    log.info("Received signal %s, shutting down...", signal.Signals(signum).name)
    stop_event.set()


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def load_config(path: Path) -> list[dict]:
    """Load and flatten all notification entries into a sorted schedule."""
    with open(path) as f:
        config = json.load(f)

    schedule = []
    for entry in config.get("notifications", []):
        event = entry.get("event", "Unknown Event")
        message = entry.get("message", event)
        event_time = entry.get("event_time", "")

        for notify_at_str in entry.get("notify_at", []):
            notify_at = datetime.fromisoformat(notify_at_str)
            if notify_at.tzinfo is None:
                notify_at = notify_at.replace(tzinfo=timezone.utc)

            schedule.append({
                "event": event,
                "message": message,
                "event_time": event_time,
                "notify_at": notify_at,
            })

    schedule.sort(key=lambda x: x["notify_at"])
    return schedule


def send_notification(entry: dict) -> bool:
    """Send notification payload to the host listener via HTTP POST."""
    payload = json.dumps({
        "title": "LearnBase",
        "subtitle": entry["event"],
        "message": entry["message"],
    }).encode("utf-8")

    req = urllib.request.Request(
        HOST_LISTENER_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            log.info("Notification sent: %s (status %d)", entry["message"], resp.status)
            return True
    except (urllib.error.URLError, OSError) as e:
        log.error("Failed to send notification for '%s': %s", entry["event"], e)
        return False


def run(schedule: list[dict]):
    """Main loop: sleep until each notification time, then fire it."""
    now = datetime.now(timezone.utc)
    pending = [e for e in schedule if e["notify_at"] > now]

    if not pending:
        log.info("No upcoming notifications (all %d are in the past). Exiting.", len(schedule))
        return

    log.info(
        "Scheduled %d notification(s), skipped %d past. Next at %s",
        len(pending),
        len(schedule) - len(pending),
        pending[0]["notify_at"].strftime("%H:%M:%S"),
    )

    for entry in pending:
        if stop_event.is_set():
            log.info("Stop requested, exiting.")
            return

        now = datetime.now(timezone.utc)
        wait_seconds = (entry["notify_at"] - now).total_seconds()

        if wait_seconds > 0:
            log.info(
                "Waiting %.0fs until %s (%s)",
                wait_seconds,
                entry["notify_at"].strftime("%H:%M:%S"),
                entry["event"],
            )
            if stop_event.wait(timeout=wait_seconds):
                log.info("Stop requested during wait, exiting.")
                return

        send_notification(entry)

    log.info("All notifications sent. Daemon will stay alive for graceful shutdown.")
    stop_event.wait()


def main():
    log.info("LearnBase notification daemon starting")

    if not CONFIG_PATH.exists():
        log.error("Config not found at %s", CONFIG_PATH)
        sys.exit(1)

    schedule = load_config(CONFIG_PATH)
    if not schedule:
        log.warning("No notifications in config. Exiting.")
        sys.exit(0)

    log.info("Loaded %d notification(s) from config", len(schedule))
    for entry in schedule:
        log.info("  %s - %s", entry["notify_at"].strftime("%H:%M:%S"), entry["message"])

    run(schedule)
    log.info("Daemon stopped.")


if __name__ == "__main__":
    main()
