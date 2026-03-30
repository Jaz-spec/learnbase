"""Google Calendar API wrapper for LearnBase."""

import json
import logging
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarManager:
    """Manages Google Calendar API access."""

    def __init__(self, token_path: Optional[Path] = None):
        if token_path is None:
            token_path = Path(__file__).parents[3] / "google-calendar" / "token.json"
        self.token_path = token_path

    def _get_credentials(self) -> Credentials:
        """Load and refresh OAuth credentials."""
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"No token found at {self.token_path}. "
                "Run google-calendar/setup_auth.py first."
            )

        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(self.token_path, "w") as f:
                f.write(creds.to_json())
            logger.info("Refreshed Google Calendar token")

        return creds

    def get_todays_events(self, calendar_id: str = "primary") -> list[dict]:
        """Fetch today's calendar events.

        Returns list of dicts with: title, start_time, end_time, attendees
        """
        creds = self._get_credentials()
        service = build("calendar", "v3", credentials=creds)

        now = datetime.now().astimezone()
        start_of_day = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        end_of_day = datetime.combine(now.date(), time.max, tzinfo=now.tzinfo)

        result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})

            # All-day events have 'date', timed events have 'dateTime'
            if "dateTime" in start:
                start_dt = datetime.fromisoformat(start["dateTime"])
                end_dt = datetime.fromisoformat(end["dateTime"])
                start_str = start_dt.strftime("%-I:%M %p")
                end_str = end_dt.strftime("%-I:%M %p")
                time_str = f"{start_str} - {end_str}"
            else:
                time_str = "All day"

            attendees = [
                a.get("email", "unknown")
                for a in item.get("attendees", [])
                if not a.get("self", False)
            ]

            events.append({
                "title": item.get("summary", "No title"),
                "time": time_str,
                "attendees": attendees,
            })

        return events
