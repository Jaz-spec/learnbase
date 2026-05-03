"""Context management tool handlers (SQLite-backed)."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.context_manager import ContextManager

logger = logging.getLogger(__name__)


# ================================================================
# Context Query Tools (existing, rewritten)
# ================================================================

def handle_get_context_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle get_context tool."""
    try:
        context = manager.get_context()

        # Format projects grouped by staleness
        fresh_projects = []
        stale_projects = []
        for project in context["projects"]:
            line = f"### {project['name']} ({project['workspace']})"
            line += f"\n  {project['description']}"
            if project["staleness"] == "stale":
                updated = project["updated_at"][:10]
                line += f"\n  **STALE** (last updated {updated})"
                stale_projects.append(line)
            else:
                fresh_projects.append(line)

        # Format people
        people_lines = [
            f"- **{p['name']}**: {p['relationship']}"
            for p in context["people"]
        ]

        sections = ["# Active Context\n"]

        if fresh_projects:
            sections.append(f"## Projects ({len(fresh_projects)} active)\n")
            sections.append("\n\n".join(fresh_projects))

        if stale_projects:
            sections.append(f"\n\n## Stale Projects ({len(stale_projects)})\n")
            sections.append("\n\n".join(stale_projects))
            sections.append(
                "\n\nThese projects haven't been updated in 2+ weeks. "
                "Use update_project to refresh or archive_project to deactivate."
            )

        if people_lines:
            sections.append(f"\n\n## People ({len(context['people'])})\n")
            sections.append("\n".join(people_lines))

        if not context["projects"] and not context["people"]:
            sections.append(
                "No projects or people found. "
                "Use add_project and add_person to set up context."
            )

        return [TextContent(type="text", text="\n".join(sections))]
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_categorize_task_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle categorize_task tool."""
    text = arguments.get("text")
    if not text:
        return [TextContent(type="text", text="Error: text is required")]

    try:
        project_id, project_confidence = manager.match_project(text)
        workspace, workspace_confidence = manager.match_workspace(project_id, text)
        categories, categories_confidence = manager.detect_categories(text)

        lines = [
            "# Auto-Categorization Results",
            "",
            f"**Text**: {text}",
            "",
            "## Suggested Categorization",
            "",
            f"**Workspace**: {workspace} (confidence: {workspace_confidence:.0%})",
            f"**Project**: {project_id or 'none'} (confidence: {project_confidence:.0%})",
            f"**Categories**: {', '.join(categories)} (confidence: {categories_confidence:.0%})",
            "",
            "## Confidence Analysis",
            "",
        ]

        if workspace_confidence < 0.6:
            lines.append(f"\u26a0\ufe0f Low confidence for workspace ({workspace_confidence:.0%}) - should ask user")
        else:
            lines.append(f"\u2713 Good confidence for workspace ({workspace_confidence:.0%})")

        if project_id and project_confidence < 0.6:
            lines.append(f"\u26a0\ufe0f Low confidence for project ({project_confidence:.0%}) - should ask user")
        elif project_id:
            lines.append(f"\u2713 Good confidence for project ({project_confidence:.0%})")

        if categories_confidence < 0.6:
            lines.append(f"\u26a0\ufe0f Low confidence for categories ({categories_confidence:.0%}) - should ask user")
        else:
            lines.append(f"\u2713 Good confidence for categories ({categories_confidence:.0%})")

        # Check if stale context was used
        if project_id:
            try:
                project = manager.get_project(project_id)
                if project["staleness"] == "stale":
                    lines.extend([
                        "",
                        f"\u26a0\ufe0f Project '{project['name']}' context is stale "
                        f"(last updated {project['updated_at'][:10]}). "
                        "Confidence reduced.",
                    ])
            except ValueError:
                pass

        lines.extend(["", "## Recommended Action", ""])

        should_ask = (
            workspace_confidence < 0.6
            or (project_id and project_confidence < 0.6)
            or categories_confidence < 0.6
        )

        if should_ask:
            lines.append("\u2753 Ask clarifying questions before creating task:")
            if workspace_confidence < 0.6:
                lines.append("  - Which workspace? (work, personal, contract)")
            if project_id and project_confidence < 0.6:
                lines.append(f"  - Is this for the {project_id} project?")
            if categories_confidence < 0.6:
                lines.append("  - What type of task? (people, idea, project, admin)")
        else:
            lines.append("\u2713 All confidence scores >= 0.6 - proceed with task creation")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        logger.error(f"Error categorizing task: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


# ================================================================
# Project Management Tools (new)
# ================================================================

def handle_add_project_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle add_project tool."""
    id = arguments.get("id")
    name = arguments.get("name")
    workspace = arguments.get("workspace")
    description = arguments.get("description")

    if not all([id, name, workspace, description]):
        return [TextContent(type="text", text="Error: id, name, workspace, and description are required")]

    try:
        project = manager.add_project(id, name, workspace, description)
        return [TextContent(
            type="text",
            text=f"Project added: **{project['name']}** ({project['workspace']})\n\n"
                 f"{project['description']}\n\nStatus: {project['staleness']}"
        )]
    except Exception as e:
        logger.error(f"Error adding project: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_update_project_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle update_project tool. Touching updated_at to refresh staleness."""
    id = arguments.get("id")
    if not id:
        return [TextContent(type="text", text="Error: id is required")]

    updates = {}
    for key in ("name", "workspace", "description"):
        if arguments.get(key) is not None:
            updates[key] = arguments[key]

    try:
        project = manager.update_project(id, **updates)
        return [TextContent(
            type="text",
            text=f"Project updated: **{project['name']}** ({project['workspace']})\n\n"
                 f"{project['description']}\n\nStatus: {project['staleness']}"
        )]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_archive_project_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle archive_project tool."""
    id = arguments.get("id")
    if not id:
        return [TextContent(type="text", text="Error: id is required")]

    try:
        project = manager.archive_project(id)
        return [TextContent(
            type="text",
            text=f"Project archived: **{project['name']}**\n\n"
                 "This project will no longer be used for task categorization."
        )]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"Error archiving project: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


# ================================================================
# People Management Tools (new)
# ================================================================

def handle_add_person_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle add_person tool."""
    id = arguments.get("id")
    name = arguments.get("name")
    relationship = arguments.get("relationship")

    if not all([id, name, relationship]):
        return [TextContent(type="text", text="Error: id, name, and relationship are required")]

    try:
        person = manager.add_person(id, name, relationship)
        return [TextContent(
            type="text",
            text=f"Person added: **{person['name']}** - {person['relationship']}"
        )]
    except Exception as e:
        logger.error(f"Error adding person: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_update_person_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle update_person tool."""
    id = arguments.get("id")
    if not id:
        return [TextContent(type="text", text="Error: id is required")]

    updates = {}
    for key in ("name", "relationship"):
        if arguments.get(key) is not None:
            updates[key] = arguments[key]

    try:
        person = manager.update_person(id, **updates)
        return [TextContent(
            type="text",
            text=f"Person updated: **{person['name']}** - {person['relationship']}"
        )]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"Error updating person: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_remove_person_tool(manager: ContextManager, arguments: Any) -> list[TextContent]:
    """Handle remove_person tool."""
    id = arguments.get("id")
    if not id:
        return [TextContent(type="text", text="Error: id is required")]

    try:
        manager.remove_person(id)
        return [TextContent(
            type="text",
            text=f"Person removed: {id}"
        )]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"Error removing person: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]
