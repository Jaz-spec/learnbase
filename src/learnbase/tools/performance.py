"""Performance tracking handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.note_manager import NoteManager

logger = logging.getLogger(__name__)


def handle_save_session_history(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """
    Handle save_session_history tool.

    Now handles BOTH:
    1. Saving session history to JSON file
    2. Updating note's question_performance frontmatter (if session includes questions)
    """
    filename = arguments.get("filename")
    session_data = arguments.get("session_data")

    if not all([filename, session_data]):
        return [TextContent(type="text", text="Error: Missing required parameters")]

    try:
        # Extract question performance data from session
        questions = session_data.get("questions", [])

        # Update note's question_performance if questions exist
        if questions:
            # Validate question structure
            for q in questions:
                if "question_hash" not in q or "score" not in q:
                    return [TextContent(
                        type="text",
                        text="Error: Each question must have question_hash and score"
                    )]
                if not (0.0 <= q["score"] <= 1.0):
                    return [TextContent(
                        type="text",
                        text=f"Error: Score must be between 0.0 and 1.0, got {q['score']}"
                    )]

            # Bulk update note frontmatter
            question_scores = [(q["question_hash"], q["score"]) for q in questions]
            note_manager.bulk_update_question_performance(filename, question_scores)

        # Save to history file (existing behavior)
        note_manager.save_session_history(filename, session_data)

        session_id = session_data.get("session_id", "unknown")
        num_questions = len(questions)

        # Enhanced result message
        result = f"✓ Session saved successfully\n\n"
        result += f"- Session ID: {session_id}\n"
        result += f"- Questions answered: {num_questions}\n"
        if num_questions > 0:
            result += f"- Note frontmatter updated with question performance\n"
        result += f"- History file: ~/.learnbase/history/{filename.replace('.md', '.json')}"

        return [TextContent(type="text", text=result)]

    except ValueError as e:
        logger.error(f"Validation error saving session: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed saving session: {e}")
        return [TextContent(type="text", text=f"Error: File operation failed: {e}")]
    except Exception as e:
        logger.critical(f"Unexpected error saving session: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: Unexpected error: {e}")]
