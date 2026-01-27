"""Tool handlers for LearnBase MCP server."""

from .notes import handle_add_note, handle_get_note, handle_list_notes, handle_edit_note, handle_delete_note
from .review import handle_get_due_notes, handle_review_note, handle_record_review
from .stats import handle_get_stats, handle_calculate_next_review
from .performance import handle_save_session_history
from .to_learn import (
    handle_add_to_learn,
    handle_list_to_learn,
    handle_get_to_learn,
    handle_remove_to_learn,
    handle_update_to_learn
)

__all__ = [
    # Note CRUD operations
    "handle_add_note",
    "handle_get_note",
    "handle_list_notes",
    "handle_edit_note",
    "handle_delete_note",
    # Review operations
    "handle_get_due_notes",
    "handle_review_note",
    "handle_record_review",
    # Stats and calculations
    "handle_get_stats",
    "handle_calculate_next_review",
    # Performance tracking
    "handle_save_session_history",
    # To-learn topic management
    "handle_add_to_learn",
    "handle_list_to_learn",
    "handle_get_to_learn",
    "handle_remove_to_learn",
    "handle_update_to_learn",
]
