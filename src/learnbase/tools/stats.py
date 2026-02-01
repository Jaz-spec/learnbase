"""Statistics and calculation handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.note_manager import NoteManager
from ..core.spaced_rep import calculate_next_review as calc_next, calculate_scheduled_review

logger = logging.getLogger(__name__)


def handle_get_stats(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle get_stats tool."""
    stats = note_manager.get_stats()

    result = "# LearnBase Statistics\n\n"
    result += f"- **Total notes**: {stats['total_notes']}\n"
    result += f"- **Review notes**: {stats['review_notes']}\n"
    result += f"- **Reference notes**: {stats['reference_notes']}\n"
    result += f"- **Reviewed today**: {stats['reviewed_today']}\n"
    result += f"- **Due today**: {stats['due_today']}\n"
    result += f"- **Due this week**: {stats['due_this_week']}\n"
    result += f"- **Average ease factor**: {stats['average_ease']:.2f}\n"
    result += f"- **Spaced repetition notes**: {stats['spaced_notes']}\n"
    result += f"- **Scheduled notes**: {stats['scheduled_notes']}"

    return [TextContent(type="text", text=result)]


def handle_calculate_next_review(note_manager: NoteManager, arguments: Any) -> list[TextContent]:
    """Handle calculate_next_review tool."""
    review_mode = arguments.get("review_mode")
    rating = arguments.get("overall_rating")
    current_interval = arguments.get("current_interval")
    ease_factor = arguments.get("ease_factor")
    review_count = arguments.get("review_count")
    schedule_pattern = arguments.get("schedule_pattern")

    if not all([review_mode, rating, current_interval is not None, ease_factor, review_count is not None]):
        return [TextContent(type="text", text="Error: Missing required parameters")]

    if rating not in [1, 2, 3, 4]:
        return [TextContent(type="text", text="Error: Rating must be between 1 and 4")]

    try:
        if review_mode == "spaced":
            new_interval, new_ease, next_review_date = calc_next(
                rating, current_interval, ease_factor, review_count
            )
        elif review_mode == "scheduled":
            if not schedule_pattern:
                return [TextContent(type="text", text="Error: schedule_pattern required for scheduled mode")]
            new_interval, next_review_date = calculate_scheduled_review(
                rating, schedule_pattern, review_count
            )
            new_ease = ease_factor  # unchanged in scheduled mode
        else:
            return [TextContent(type="text", text="Error: review_mode must be 'spaced' or 'scheduled'")]

        result = f"**Next Review Calculated**\n\n"
        result += f"- Next review date: {next_review_date.strftime('%Y-%m-%d')}\n"
        result += f"- Interval: {new_interval} days\n"
        result += f"- Ease factor: {new_ease:.2f}\n"
        result += f"- Review count: {review_count + 1}"

        return [TextContent(type="text", text=result)]

    except ValueError as e:
        logger.error(f"Validation error calculating next review: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.critical(f"Unexpected error calculating next review: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: Unexpected error: {e}")]
