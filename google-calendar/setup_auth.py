"""One-time OAuth setup for Google Calendar API.

Run this script to authorize LearnBase to read your Google Calendar.
It will open a browser for consent and save the token locally.

Usage:
    python google-calendar/setup_auth.py
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print(f"Token saved to {TOKEN_FILE}")
    print("You can now restart Claude Code to use the calendar integration.")


if __name__ == "__main__":
    main()
