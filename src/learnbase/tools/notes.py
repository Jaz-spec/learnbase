"""Note CRUD operation handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.note_manager import NoteManager

logger = logging.getLogger(__name__)


def handle_add_note(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle add_note tool."""
    title = arguments.get("title")
    body = arguments.get("body")
    review_mode = arguments.get("review_mode", "spaced")
    schedule_pattern = arguments.get("schedule_pattern")

    if not title or not body:
        return [TextContent(
            type="text",
            text="Error: title and body are required"
        )]

    try:
        filename = note_manager.create_note(title, body, review_mode, schedule_pattern)

        return [TextContent(
            type="text",
            text=f"✓ Created note: {filename}\nTitle: {title}\nMode: {review_mode}\nNext review: today"
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

    result = note.format_full()

    return [TextContent(type="text", text=result)]


def handle_list_notes(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle list_notes tool."""
    due_only = arguments.get("due_only", False)
    limit = arguments.get("limit")

    if due_only:
        notes = note_manager.get_due_notes(limit=limit)
        header = "Notes due for review"
    else:
        notes = note_manager.get_all_notes()
        if limit:
            notes = notes[:limit]
        header = "All notes"

    if not notes:
        return [TextContent(
            type="text",
            text="No notes found."
        )]

    result = f"## {header}\n\n"
    for note in notes:
        days = note.days_until_review()
        if days < 0:
            status = f"overdue by {-days} days"
        elif days == 0:
            status = "due today"
        else:
            status = f"due in {days} days"

        result += f"### {note.title}\n"
        result += f"- **File**: {note.filename}\n"
        result += f"- **Status**: {status}\n"
        result += f"- **Mode**: {note.review_mode}\n"
        result += f"- **Reviews**: {note.review_count}, **Ease**: {note.ease_factor:.2f}\n\n"

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
