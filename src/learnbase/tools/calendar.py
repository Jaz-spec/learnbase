"""Calendar tool handlers for LearnBase MCP server."""

import logging
from mcp.types import TextContent

logger = logging.getLogger(__name__)


def handle_get_calendar_events(calendar_manager, arguments: dict) -> list[TextContent]:
    """Get today's Google Calendar events."""
    try:
        calendar_id = arguments.get("calendar_id", "primary")
        events = calendar_manager.get_todays_events(calendar_id)

        if not events:
            return [TextContent(type="text", text="No events scheduled for today.")]

        lines = []
        for event in events:
            lines.append(f"## {event['title']}")
            lines.append(f"- **Time**: {event['time']}")
            attendees = ", ".join(event["attendees"]) if event["attendees"] else "None listed"
            lines.append(f"- **Attendees**: {attendees}")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    except FileNotFoundError as e:
        return [TextContent(type="text", text=f"Calendar not configured: {e}")]
    except Exception as e:
        logger.error(f"Calendar error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error fetching calendar events: {e}")]
