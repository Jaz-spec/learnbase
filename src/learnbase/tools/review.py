"""Review operation handlers."""

import logging
from datetime import datetime
from typing import Any
from mcp.types import TextContent

from ..core.note_manager import NoteManager
from ..core.models import Note

logger = logging.getLogger(__name__)


def _get_verification_status_indicator(note: Note) -> str:
    """
    Get verification status indicator for a note.

    Args:
        note: Note instance

    Returns:
        Status indicator string
    """
    if not note.sources:
        return " ⚠️ [UNVERIFIED]"
    if note.confidence_score is not None and note.confidence_score < 0.6:
        return f" ⚠️ [LOW CONFIDENCE: {note.confidence_score:.2f}]"
    return ""

def handle_get_due_notes(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle get_due_notes tool."""
    limit = arguments.get("limit")
    review_mode = arguments.get("review_mode")
    require_verified = arguments.get("require_verified", False)

    notes = note_manager.get_due_notes(
        limit=limit,
        review_mode=review_mode,
        require_verified=require_verified
    )

    if not notes:
        return [TextContent(
            type="text",
            text="No notes are currently due for review."
        )]

    result = f"Found {len(notes)} note(s) due for review:\n\n"
    for note in notes:
        # Calculate days since last review
        if note.last_reviewed:
            days_ago = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) -
                       note.last_reviewed.replace(hour=0, minute=0, second=0, microsecond=0)).days
            if days_ago == 0:
                last_reviewed_text = "today"
            elif days_ago == 1:
                last_reviewed_text = "1 day ago"
            else:
                last_reviewed_text = f"{days_ago} days ago"
        else:
            last_reviewed_text = "Never"

        result += f"{note.filename}\n"
        result += f"   Title: {note.title}\n"
        result += f"   Mode: {note.review_mode}\n"
        result += f"   Last reviewed: {last_reviewed_text}\n"
        result += f"   Review count: {note.review_count}\n"

        # Add verification status with confidence score
        if not note.sources:
            confidence = note.confidence_score if note.confidence_score is not None else 0.0
            result += f"   Verification: Un-verified (confidence: {confidence:.2f})\n"
        else:
            confidence = note.confidence_score if note.confidence_score is not None else 0.0
            result += f"   Verification: Verified - {len(note.sources)} source(s) (confidence: {confidence:.2f})\n"

        result += "\n"

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
