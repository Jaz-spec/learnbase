"""MCP server for LearnBase."""

import asyncio
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .core.note_manager import NoteManager
from .core.to_learn_manager import ToLearnManager
from .core.rag_manager import RAGManager
from .core.tasks_manager import TasksManager
from .core.daily_manager import DailyManager
from .core.context_parser import ContextParser
from .core.calendar_manager import CalendarManager
from .tools import (
    handle_add_note,
    handle_get_note,
    handle_list_notes,
    handle_edit_note,
    handle_delete_note,
    handle_get_due_notes,
    handle_review_note,
    handle_record_review,
    handle_get_stats,
    handle_calculate_next_review,
    handle_save_session_history,
    handle_add_to_learn,
    handle_list_to_learn,
    handle_get_to_learn,
    handle_remove_to_learn,
    handle_update_to_learn,
    handle_index_note,
    handle_search_notes,
    handle_remove_from_index,
    handle_reindex_all_notes,
    handle_get_index_stats,
)
from .tools.tasks import (
    handle_create_task_tool,
    handle_get_task_tool,
    handle_list_tasks_tool,
    handle_update_task_tool,
    handle_archive_task_tool,
)
from .tools.daily import (
    handle_create_daily_plan_tool,
    handle_update_daily_reflection_tool,
)
from .tools.context import (
    handle_get_context_tool,
    handle_categorize_task_tool,
)
from .tools.calendar import handle_get_calendar_events


def setup_logging():
    """Configure logging for LearnBase MCP server."""
    log_dir = Path.home() / ".learnbase"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "learnbase.log"

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=10_485_760, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    logging.getLogger('learnbase').setLevel(logging.DEBUG)
    logging.info("LearnBase MCP server starting")

setup_logging()

app = Server("learnbase")

# Initialize managers with proper dependency injection
# Step 1: Create note_manager without rag_manager
note_manager = NoteManager()

# Step 2: Create rag_manager with note_manager
rag_manager = RAGManager(note_manager)

# Step 3: Inject rag_manager back into note_manager for auto-indexing
note_manager.rag_manager = rag_manager

# Initialize to_learn_manager independently
to_learn_manager = ToLearnManager()

# Initialize task management system
tasks_manager = TasksManager()
daily_manager = DailyManager(tasks_manager)
context_parser = ContextParser()
calendar_manager = CalendarManager()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="add_note",
            description="Add a new learning note to LearnBase. Can create review notes (spaced repetition) or reference notes (storage only).",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The note title/topic"
                    },
                    "body": {
                        "type": "string",
                        "description": "Markdown content of the note"
                    },
                    "note_type": {
                        "type": "string",
                        "enum": ["review", "reference", "evergreen"],
                        "description": "Type of note: 'review' for spaced repetition learning, 'reference' for storage only, 'evergreen' for manual curation (LLM read-only). Default: 'review'",
                        "default": "review"
                    },
                    "review_mode": {
                        "type": "string",
                        "enum": ["spaced", "scheduled"],
                        "description": "Review mode (only for review notes): 'spaced' for SM-2 algorithm, 'scheduled' for fixed intervals. Default: 'spaced'"
                    },
                    "schedule_pattern": {
                        "type": "string",
                        "description": "Schedule pattern (only for scheduled review mode, e.g., '1d,1w,2w,1m')"
                    }
                },
                "required": ["title", "body"]
            }
        ),
        Tool(
            name="get_due_notes",
            description="Get notes that are due for review. After calling this, read ~/.claude/skills/learnbase/SKILL.md for the complete review protocol.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of notes to return (optional)"
                    },
                    "review_mode": {
                        "type": "string",
                        "enum": ["spaced", "scheduled"],
                        "description": "Filter by review mode (optional)"
                    },
                    "require_verified": {
                        "type": "boolean",
                        "description": "Only include verified notes (with sources and confidence >= 0.6). Default: false"
                    }
                }
            }
        ),
        Tool(
            name="review_note",
            description="Get a note for review (question generation handled by Skill)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename (e.g., 'python-gil.md')"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="record_review",
            description="Record the result of reviewing a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename"
                    },
                    "rating": {
                        "type": "number",
                        "description": "Rating from 1-4: 1=poor, 2=fair, 3=good, 4=excellent",
                        "minimum": 1,
                        "maximum": 4
                    }
                },
                "required": ["filename", "rating"]
            }
        ),
        Tool(
            name="list_notes",
            description="List all notes with metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "due_only": {
                        "type": "boolean",
                        "description": "Only show notes due for review"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of notes to return"
                    },
                    "needs_verification": {
                        "type": "boolean",
                        "description": "Only show notes with no sources (need verification)"
                    },
                    "low_confidence_threshold": {
                        "type": "number",
                        "description": "Show notes with confidence score below this threshold (0.0-1.0). Default: 0.6"
                    },
                    "exclude_unverified": {
                        "type": "boolean",
                        "description": "Exclude notes without sources from results"
                    },
                    "note_type": {
                        "type": "string",
                        "enum": ["review", "reference", "evergreen"],
                        "description": "Filter by note type: 'review', 'reference', or 'evergreen'"
                    }
                }
            }
        ),
        Tool(
            name="get_note",
            description="Get the full content of a specific note",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="edit_note",
            description="Update the content of a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "body": {
                        "type": "string",
                        "description": "New markdown content (optional)"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="delete_note",
            description="Delete a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="get_stats",
            description="Get learning statistics from LearnBase",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="calculate_next_review",
            description="Calculate next review date using SM-2 algorithm or scheduled pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "review_mode": {
                        "type": "string",
                        "enum": ["spaced", "scheduled"],
                        "description": "Review mode"
                    },
                    "overall_rating": {
                        "type": "number",
                        "description": "Overall confidence rating (1-4)",
                        "minimum": 1,
                        "maximum": 4
                    },
                    "current_interval": {
                        "type": "number",
                        "description": "Current interval in days"
                    },
                    "ease_factor": {
                        "type": "number",
                        "description": "Current ease factor"
                    },
                    "review_count": {
                        "type": "number",
                        "description": "Number of times reviewed"
                    },
                    "schedule_pattern": {
                        "type": "string",
                        "description": "Schedule pattern for scheduled mode (e.g., '1d,1w,2w,1m')"
                    }
                },
                "required": ["review_mode", "overall_rating", "current_interval", "ease_factor", "review_count"]
            }
        ),
        Tool(
            name="save_session_history",
            description="Save complete session data to history file and update note's question performance. Call ONCE at end of review session with all question data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Note filename"
                    },
                    "session_data": {
                        "type": "object",
                        "description": "Session data including questions array with question_hash and score for each question",
                        "properties": {
                            "session_id": {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "question_hash": {
                                            "type": "string",
                                            "description": "MD5 hash of question"
                                        },
                                        "score": {
                                            "type": "number",
                                            "minimum": 0.0,
                                            "maximum": 1.0
                                        },
                                        "question_text": {"type": "string"},
                                        "user_answer": {"type": "string"},
                                        "evaluation": {"type": "string"},
                                        "follow_ups": {"type": "number"},
                                        "user_had_questions": {"type": "boolean"}
                                    },
                                    "required": ["question_hash", "score"]
                                }
                            },
                            "overall_rating": {"type": "number"},
                            "average_score": {"type": "number"},
                            "learned_content": {"type": "array"},
                            "priorities_requested": {
                                "type": "array",
                                "description": "New priority requests made during this session",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "topic": {"type": "string"},
                                        "reason": {"type": "string"}
                                    },
                                    "required": ["topic"]
                                }
                            },
                            "priorities_addressed": {
                                "type": "array",
                                "description": "List of priority topics that were covered in this session",
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["filename", "session_data"]
            }
        ),
        # To-learn topic management
        Tool(
            name="add_to_learn",
            description="Add a topic to your learning list. Use this when you want to remember something to learn later.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic name"
                    },
                    "context": {
                        "type": "string",
                        "description": "What is this topic related to? (e.g., 'encryption', 'networking', 'linked in')"
                    },
                    "detailed": {
                        "type": "boolean",
                        "description": "If true, add to detailed section; if false, add to quick table",
                        "default": False
                    },
                    "notes": {
                        "type": "string",
                        "description": "Detailed notes (only used if detailed=true)"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="list_to_learn",
            description="List all topics you want to learn about.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_archived": {
                        "type": "boolean",
                        "description": "Include archived topics",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_to_learn",
            description="Get detailed information about a specific learning topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic name"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="remove_to_learn",
            description="Archive a topic (moves to Archive section). Use when you've learned it or no longer need it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic name"
                    }
                },
                "required": ["topic"]
            }
        ),
        Tool(
            name="update_to_learn",
            description="Update notes or context for an existing learning topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic name"
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes"
                    },
                    "context": {
                        "type": "string",
                        "description": "New context - what the topic is related to"
                    }
                },
                "required": ["topic"]
            }
        ),
        # RAG / Semantic Search tools
        Tool(
            name="index_note",
            description="Index a note in the vector database for semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename to index (e.g., 'python-gil.md')"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="search_notes",
            description="Search notes using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language)"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence score for review notes (0.0-1.0)"
                    },
                    "note_type": {
                        "type": "string",
                        "enum": ["review", "reference", "evergreen"],
                        "description": "Filter by note type"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="remove_from_index",
            description="Remove a note from the vector database index",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The note filename to remove from index"
                    }
                },
                "required": ["filename"]
            }
        ),
        Tool(
            name="reindex_all_notes",
            description="Rebuild the entire vector database index from all notes",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_index_stats",
            description="Get statistics about the vector database index",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        # Task Management tools
        Tool(
            name="create_task",
            description="Create a new task with auto-categorization",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Task description (markdown)"
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date/time (ISO 8601 datetime)"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task categories (people, idea, project, admin)"
                    },
                    "workspace": {
                        "type": "string",
                        "enum": ["work", "personal", "contract"],
                        "description": "Workspace"
                    },
                    "project": {
                        "type": "string",
                        "description": "Project name (from active-context)"
                    },
                    "confidence": {
                        "type": "object",
                        "description": "Confidence scores for auto-categorization"
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Explanation of categorization choices"
                    }
                },
                "required": ["title", "due"]
            }
        ),
        Tool(
            name="get_task",
            description="Get a task by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID (e.g., '2026-02-03-call-dan')"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="list_tasks",
            description="List tasks with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Filter by status"
                    },
                    "workspace": {
                        "type": "string",
                        "enum": ["work", "personal", "contract"],
                        "description": "Filter by workspace"
                    },
                    "project": {
                        "type": "string",
                        "description": "Filter by project name"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by categories (must have ALL)"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Filter by due date (ISO 8601)"
                    }
                }
            }
        ),
        Tool(
            name="update_task",
            description="Update task fields",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    },
                    "updates": {
                        "type": "object",
                        "description": "Dictionary of fields to update"
                    }
                },
                "required": ["task_id", "updates"]
            }
        ),
        Tool(
            name="archive_task",
            description="Archive a completed task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        # Daily Workflow tools
        Tool(
            name="create_daily_plan",
            description="Generate daily task list for morning workflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Optional date (ISO 8601, defaults to today)"
                    }
                }
            }
        ),
        Tool(
            name="update_daily_reflection",
            description="Update tasks with evening reflection",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date (ISO 8601)"
                    },
                    "completed": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Completed tasks [{task_id, notes}, ...]"
                    },
                    "incomplete": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Incomplete tasks [{task_id, reason, rollover}, ...]"
                    },
                    "new_tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New task IDs created during reflection"
                    },
                    "reflection_notes": {
                        "type": "string",
                        "description": "General reflection notes"
                    }
                },
                "required": ["date", "completed", "incomplete"]
            }
        ),
        # Context tools
        Tool(
            name="get_context",
            description="Get structured context from active-context/index.md",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="categorize_task",
            description="Auto-categorize task from natural language with confidence scoring",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "User's task description text"
                    }
                },
                "required": ["text"]
            }
        ),
        # Calendar tools
        Tool(
            name="get_calendar_events",
            description="Get today's Google Calendar events with meeting name, time, and attendees",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "Calendar ID (default: 'primary')",
                        "default": "primary"
                    }
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls by dispatching to appropriate handler."""

    # Tool dispatch table
    handlers = {
        # Note CRUD operations
        "add_note": handle_add_note,
        "get_note": handle_get_note,
        "list_notes": handle_list_notes,
        "edit_note": handle_edit_note,
        "delete_note": handle_delete_note,
        # Review operations
        "get_due_notes": handle_get_due_notes,
        "review_note": handle_review_note,
        "record_review": handle_record_review,
        # Stats and calculations
        "get_stats": handle_get_stats,
        "calculate_next_review": handle_calculate_next_review,
        # Performance tracking
        "save_session_history": handle_save_session_history,
        # To-learn topic management
        "add_to_learn": handle_add_to_learn,
        "list_to_learn": handle_list_to_learn,
        "get_to_learn": handle_get_to_learn,
        "remove_to_learn": handle_remove_to_learn,
        "update_to_learn": handle_update_to_learn,
        # RAG operations
        "index_note": handle_index_note,
        "search_notes": handle_search_notes,
        "remove_from_index": handle_remove_from_index,
        "reindex_all_notes": handle_reindex_all_notes,
        "get_index_stats": handle_get_index_stats,
        # Task management
        "create_task": handle_create_task_tool,
        "get_task": handle_get_task_tool,
        "list_tasks": handle_list_tasks_tool,
        "update_task": handle_update_task_tool,
        "archive_task": handle_archive_task_tool,
        # Daily workflow
        "create_daily_plan": handle_create_daily_plan_tool,
        "update_daily_reflection": handle_update_daily_reflection_tool,
        # Context tools
        "get_context": handle_get_context_tool,
        "categorize_task": handle_categorize_task_tool,
        # Calendar tools
        "get_calendar_events": handle_get_calendar_events,
    }

    # Dispatch to handler
    handler = handlers.get(name)
    if handler:
        # Use to_learn_manager for to-learn tools
        if name.startswith("add_to_learn") or name.startswith("list_to_learn") or \
           name.startswith("get_to_learn") or name.startswith("remove_to_learn") or \
           name.startswith("update_to_learn"):
            return handler(to_learn_manager, arguments)
        # Use rag_manager for RAG tools
        elif name in ("index_note", "search_notes", "remove_from_index",
                      "reindex_all_notes", "get_index_stats"):
            return handler(rag_manager, arguments)
        # Use tasks_manager for task management tools
        elif name in ("create_task", "get_task", "list_tasks", "update_task", "archive_task"):
            return handler(tasks_manager, arguments)
        # Use daily_manager for daily workflow tools
        elif name in ("create_daily_plan", "update_daily_reflection"):
            return handler(daily_manager, arguments)
        # Use context_parser for context tools
        elif name in ("get_context", "categorize_task"):
            return handler(context_parser, arguments)
        # Use calendar_manager for calendar tools
        elif name == "get_calendar_events":
            return handler(calendar_manager, arguments)
        # Use note_manager for everything else
        else:
            return handler(note_manager, arguments)
    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'"
        )]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
