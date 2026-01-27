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
)


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
note_manager = NoteManager()
to_learn_manager = ToLearnManager()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="add_note",
            description="Add a new learning note to LearnBase",
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
                    "review_mode": {
                        "type": "string",
                        "enum": ["spaced", "scheduled"],
                        "description": "Review mode: 'spaced' for SM-2 algorithm, 'scheduled' for fixed intervals",
                        "default": "spaced"
                    },
                    "schedule_pattern": {
                        "type": "string",
                        "description": "Schedule pattern for scheduled mode (e.g., '1d,1w,2w,1m')"
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
        )
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
    }

    # Dispatch to handler
    handler = handlers.get(name)
    if handler:
        # Use to_learn_manager for to-learn tools, note_manager for others
        if name.startswith("add_to_learn") or name.startswith("list_to_learn") or \
           name.startswith("get_to_learn") or name.startswith("remove_to_learn") or \
           name.startswith("update_to_learn"):
            return handler(to_learn_manager, arguments)
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
