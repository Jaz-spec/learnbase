"""Note CRUD operation handlers."""

import logging
from typing import Any, Literal
from mcp.types import TextContent

from ..core.note_manager import NoteManager
from ..core.models import Note, ReviewNote, ReferenceNote, EvergreenNote

logger = logging.getLogger(__name__)


def _get_verification_status(note: Note) -> Literal["unverified", "low_confidence", "verified", "reference"]:
    """
    Determine verification status for a note.

    Args:
        note: Note instance

    Returns:
        Verification status: "unverified", "low_confidence", "verified", or "reference"
    """
    if isinstance(note, ReferenceNote):
        return "reference"
    if not note.sources:
        return "unverified"
    if note.confidence_score is not None and note.confidence_score < 0.6:
        return "low_confidence"
    return "verified"


def handle_add_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle add_note tool."""
    title = arguments.get("title")
    body = arguments.get("body")
    note_type = arguments.get("note_type", "review")  # Default to review
    review_mode = arguments.get("review_mode")
    schedule_pattern = arguments.get("schedule_pattern")

    if not title or not body:
        return [TextContent(
            type="text",
            text="Error: title and body are required"
        )]

    try:
        filename = note_manager.create_note(
            title=title,
            body=body,
            note_type=note_type,
            review_mode=review_mode,
            schedule_pattern=schedule_pattern
        )

        if note_type == 'reference':
            return [TextContent(
                type="text",
                text=f"✓ Created reference note: {filename}\nTitle: {title}\nType: Reference (storage only)"
            )]
        elif note_type == 'evergreen':
            return [TextContent(
                type="text",
                text=f"✓ Created evergreen note: {filename}\nTitle: {title}\nType: Evergreen (manually curated - LLM read-only)"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"✓ Created review note: {filename}\nTitle: {title}\nMode: {review_mode or 'spaced'}\nNext review: today"
            )]
    except ValueError as e:
        logger.error(f"Validation error creating note: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed creating note: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error creating note: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_get_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle get_note tool."""
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

    # Format differently based on note type
    if isinstance(note, ReviewNote):
        result = note.format_full()
    elif isinstance(note, EvergreenNote):
        result = f"# {note.title}\n\n"
        result += f"**File**: {note.filename}\n"
        result += f"**Type**: Evergreen (manually curated)\n\n"
        result += "---\n\n"
        result += note.body
    else:  # ReferenceNote
        result = f"# {note.title}\n\n"
        result += f"**File**: {note.filename}\n"
        result += f"**Type**: Reference\n\n"
        result += "---\n\n"
        result += note.body

    return [TextContent(type="text", text=result)]


def handle_list_notes(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle list_notes tool."""
    due_only = arguments.get("due_only", False)
    limit = arguments.get("limit")
    needs_verification = arguments.get("needs_verification", False)
    low_confidence_threshold = arguments.get("low_confidence_threshold")
    exclude_unverified = arguments.get("exclude_unverified", False)
    note_type = arguments.get("note_type")

    # Determine which notes to fetch
    if needs_verification:
        notes = note_manager.get_notes_needing_verification(limit=limit)
        header = "Notes needing verification (no sources)"
    elif low_confidence_threshold is not None:
        notes = note_manager.get_notes_with_low_confidence(
            threshold=low_confidence_threshold,
            limit=limit
        )
        header = f"Notes with confidence < {low_confidence_threshold}"
    elif due_only:
        notes = note_manager.get_due_notes(limit=limit)
        header = "Notes due for review"
    elif note_type:
        notes = note_manager.get_all_notes_by_type(note_type=note_type)
        if limit:
            notes = notes[:limit]
        header = f"{note_type.capitalize()} notes"
    else:
        notes = note_manager.get_all_notes()
        if limit:
            notes = notes[:limit]
        header = "All notes"

    # Apply exclude_unverified filter if requested
    if exclude_unverified and not (needs_verification or low_confidence_threshold):
        notes = [n for n in notes if n.sources]

    if not notes:
        return [TextContent(
            type="text",
            text="No notes found."
        )]

    result = f"## {header}\n\n"
    for note in notes:
        if isinstance(note, ReviewNote):
            days = note.days_until_review()
            if days < 0:
                status = f"overdue by {-days} days"
            elif days == 0:
                status = "due today"
            else:
                status = f"due in {days} days"

            # Get verification status
            verification_status = _get_verification_status(note)

            # Add visual indicator
            verification_indicator = ""
            if verification_status == "unverified":
                verification_indicator = " ⚠️ [UNVERIFIED]"
            elif verification_status == "low_confidence":
                verification_indicator = f" ⚠️ [LOW CONFIDENCE: {note.confidence_score:.2f}]"

            result += f"### {note.title}{verification_indicator}\n"
            result += f"- **File**: {note.filename}\n"
            result += f"- **Status**: {status}\n"
            result += f"- **Mode**: {note.review_mode}\n"
            result += f"- **Reviews**: {note.review_count}, **Ease**: {note.ease_factor:.2f}\n"
            result += f"- **Verification**: {verification_status}"
            if note.confidence_score is not None:
                result += f", **Confidence**: {note.confidence_score:.2f}"
            result += f", **Sources**: {len(note.sources)}\n\n"
        elif isinstance(note, EvergreenNote):
            result += f"### {note.title}\n"
            result += f"- **File**: {note.filename}\n"
            result += f"- **Type**: Evergreen (manually curated)\n\n"
        else:  # ReferenceNote
            result += f"### {note.title}\n"
            result += f"- **File**: {note.filename}\n"
            result += f"- **Type**: Reference\n\n"

    return [TextContent(type="text", text=result)]


def handle_edit_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle edit_note tool."""
    filename = arguments.get("filename")
    title = arguments.get("title")
    body = arguments.get("body")

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

    # Update fields if provided
    new_title = title if title else note.title
    new_body = body if body else note.body

    try:
        note_manager.update_note_content(filename, new_title, new_body)

        return [TextContent(
            type="text",
            text=f"✓ Updated note: {filename}\nTitle: {new_title}"
        )]
    except ValueError as e:
        logger.error(f"Validation error updating note: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed updating note: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error updating note: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_delete_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle delete_note tool."""
    filename = arguments.get("filename")

    if not filename:
        return [TextContent(
            type="text",
            text="Error: filename is required"
        )]

    success = note_manager.delete_note(filename)

    if success:
        return [TextContent(
            type="text",
            text=f"✓ Deleted note: {filename}"
        )]
    else:
        return [TextContent(
            type="text",
            text=f"Error: Note {filename} not found"
        )]
