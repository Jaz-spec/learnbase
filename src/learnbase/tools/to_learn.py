"""Tool handlers for to-learn topics management."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.to_learn_manager import ToLearnManager

logger = logging.getLogger(__name__)


def handle_add_to_learn(to_learn_manager: ToLearnManager, arguments: Any) -> list[TextContent]:
    """Handle add_to_learn tool."""
    topic = arguments.get("topic")
    context = arguments.get("context", "")
    detailed = arguments.get("detailed", False)
    notes = arguments.get("notes", "")

    if not topic:
        return [TextContent(
            type="text",
            text="Error: topic is required"
        )]

    try:
        to_learn_manager.add_topic(
            topic=topic,
            context=context,
            detailed=detailed,
            notes=notes
        )

        result = f"✓ Added {'detailed' if detailed else 'quick'} topic: {topic}\n"
        result += f"Context: {context}" if context else "No context specified"

        return [TextContent(type="text", text=result)]

    except ValueError as e:
        logger.error(f"Validation error adding topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed adding topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error adding topic: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_list_to_learn(to_learn_manager: ToLearnManager, arguments: Any) -> list[TextContent]:
    """Handle list_to_learn tool."""
    include_archived = arguments.get("include_archived", False)

    try:
        topics = to_learn_manager.list_topics(
            include_archived=include_archived
        )

        if not topics:
            return [TextContent(type="text", text="No topics found.")]

        # Build header
        if include_archived:
            header = "## All topics (including archived)"
        else:
            header = "## Topics to learn"

        result = f"{header}\n\n"

        # Group by type
        quick_topics = [t for t in topics if not t.get("detailed")]
        detailed_topics = [t for t in topics if t.get("detailed") and not t.get("archived")]
        archived_topics = [t for t in topics if t.get("archived")]

        # Show quick topics
        if quick_topics:
            result += "### Quick Capture Topics\n\n"
            for topic in quick_topics:
                context_str = f" | {topic['context']}" if topic.get('context') else ""
                result += f"**{topic['topic']}**{context_str}\n"
                result += f"- Added: {topic['added']}\n"
                result += "\n"

        # Show detailed topics
        if detailed_topics:
            result += "### Detailed Topics\n\n"
            for topic in detailed_topics:
                context_str = f" | {topic['context']}" if topic.get('context') else ""
                result += f"**{topic['topic']}**{context_str}\n"
                result += f"- Added: {topic['added']}\n"
                if topic.get('notes'):
                    # Show first line of notes as preview
                    first_line = topic['notes'].split('\n')[0][:80]
                    result += f"- Notes: {first_line}...\n"
                result += "\n"

        # Show archived topics
        if archived_topics:
            result += "### Archived Topics\n\n"
            for topic in archived_topics:
                context_str = f" | {topic['context']}" if topic.get('context') else ""
                result += f"**{topic['topic']}**{context_str}\n"
                result += f"- Added: {topic['added']}\n"
                if topic.get('completed'):
                    result += f"- Completed: {topic['completed']}\n"
                result += "\n"

        return [TextContent(type="text", text=result)]

    except Exception as e:
        logger.critical(f"Unexpected error listing topics: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_get_to_learn(to_learn_manager: ToLearnManager, arguments: Any) -> list[TextContent]:
    """Handle get_to_learn tool."""
    topic = arguments.get("topic")

    if not topic:
        return [TextContent(
            type="text",
            text="Error: topic is required"
        )]

    try:
        topic_data = to_learn_manager.get_topic(topic)

        if not topic_data:
            return [TextContent(
                type="text",
                text=f"Topic '{topic}' not found."
            )]

        # Format full topic details
        result = f"# {topic_data['topic']}\n\n"
        result += f"**Added:** {topic_data['added']}\n"

        if topic_data.get('context'):
            result += f"**Context:** {topic_data['context']}\n"

        if topic_data.get('completed'):
            result += f"**Completed:** {topic_data['completed']}\n"

        if topic_data.get('archived'):
            result += f"**Archived:** Yes\n"

        result += "\n"

        if topic_data.get('notes'):
            result += "## Notes\n\n"
            result += topic_data['notes']

        return [TextContent(type="text", text=result)]

    except ValueError as e:
        logger.error(f"Validation error getting topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error getting topic: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_remove_to_learn(to_learn_manager: ToLearnManager, arguments: Any) -> list[TextContent]:
    """Handle remove_to_learn tool."""
    topic = arguments.get("topic")

    if not topic:
        return [TextContent(
            type="text",
            text="Error: topic is required"
        )]

    try:
        success = to_learn_manager.remove_topic(topic)

        if success:
            return [TextContent(
                type="text",
                text=f"✓ Archived topic: {topic}\n\nThe topic has been moved to the Archive section."
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Topic '{topic}' not found."
            )]

    except ValueError as e:
        logger.error(f"Validation error removing topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed removing topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error removing topic: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


def handle_update_to_learn(to_learn_manager: ToLearnManager, arguments: Any) -> list[TextContent]:
    """Handle update_to_learn tool."""
    topic = arguments.get("topic")
    notes = arguments.get("notes")
    context = arguments.get("context")

    if not topic:
        return [TextContent(
            type="text",
            text="Error: topic is required"
        )]

    if notes is None and context is None:
        return [TextContent(
            type="text",
            text="Error: At least one of notes or context must be provided"
        )]

    try:
        success = to_learn_manager.update_topic(
            topic=topic,
            notes=notes,
            context=context
        )

        if success:
            updates = []
            if notes is not None:
                updates.append("notes")
            if context is not None:
                updates.append(f"context to '{context}'")

            return [TextContent(
                type="text",
                text=f"✓ Updated {topic}\n\nChanged: {', '.join(updates)}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Topic '{topic}' not found."
            )]

    except ValueError as e:
        logger.error(f"Validation error updating topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed updating topic: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
    except Exception as e:
        logger.critical(f"Unexpected error updating topic: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: Unexpected error: {e}"
        )]


