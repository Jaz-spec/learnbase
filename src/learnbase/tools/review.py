"""Review operation handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.note_manager import NoteManager

logger = logging.getLogger(__name__)

def handle_get_due_notes(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle get_due_notes tool."""
    limit = arguments.get("limit")
    review_mode = arguments.get("review_mode")

    notes = note_manager.get_due_notes(limit=limit, review_mode=review_mode)

    if not notes:
        return [TextContent(
            type="text",
            text="No notes are currently due for review."
        )]

    result = f"Found {len(notes)} note(s) due for review:\n\n"
    for note in notes:
        result += f"📝 {note.filename}\n"
        result += f"   Title: {note.title}\n"
        result += f"   Mode: {note.review_mode}\n"
        result += f"   Last reviewed: {note.last_reviewed.strftime('%Y-%m-%d') if note.last_reviewed else 'Never'}\n"
        result += f"   Review count: {note.review_count}\n\n"

    return [TextContent(type="text", text=result)]


def handle_review_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle review_note tool."""
    filename = arguments.get("filename")

    if not filename:
        return [TextContent(
            type="text",
            text="Error: filename is required"
        )]

    note = note_manager.get_note(filename)
    if not note:
        return [TextContent(
            type="text",
            text=f"Error: Note {filename} not found"
        )]

    # Build response with note content
    result = f"# {note.title}\n\n"
    result += f"**File**: {note.filename}\n"
    result += f"**Mode**: {note.review_mode}\n"
    result += f"**Reviews**: {note.review_count}\n"
    result += f"**Ease factor**: {note.ease_factor:.2f}\n\n"
    result += "---\n\n"
    result += note.body

    return [TextContent(type="text", text=result)]


def handle_record_review(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle record_review tool."""
    filename = arguments.get("filename")
    rating = arguments.get("rating")

    if not filename or rating is None:
        return [TextContent(
            type="text",
            text="Error: filename and rating are required"
        )]

    if rating not in [1, 2, 3, 4]:
        return [TextContent(
            type="text",
            text="Error: rating must be between 1 and 4"
        )]

    try:
        note_manager.update_note_review(filename, rating)
        updated_note = note_manager.get_note(filename)

        rating_text = {
            1: "poor (need to review again soon)",
            2: "fair (somewhat understood)",
            3: "good (well understood)",
            4: "excellent (perfect recall)"
        }

        result = f"✓ Reviewed: {updated_note.title}\n"
        result += f"Rating: {rating} - {rating_text[rating]}\n"
        result += f"Next review: in {updated_note.interval_days} day(s)\n"
        result += f"Ease factor: {updated_note.ease_factor:.2f}\n"
        result += f"Total reviews: {updated_note.review_count}"

        return [TextContent(type="text", text=result)]

    except ValueError as e:
        logger.error(f"Validation error recording review: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed recording review: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error recording review: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]
