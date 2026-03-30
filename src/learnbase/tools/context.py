"""Active context operation handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.context_parser import ContextParser

logger = logging.getLogger(__name__)


def handle_get_context_tool(parser: ContextParser, arguments: Any) -> list[TextContent]:
    """Handle get_context tool."""
    try:
        context = parser.get_context()

        # Format projects
        projects_text = []
        for project in context['projects']:
            projects_text.append(f"### {project['name']} ({project['workspace']})")
            projects_text.append(f"  People: {', '.join(project['people']) if project['people'] else 'none'}")
            projects_text.append(f"  Keywords: {', '.join(project['keywords'][:10])}")
            projects_text.append("")

        # Format people
        people_text = []
        for name, projects in context['people'].items():
            people_text.append(f"- **{name}**: {', '.join(projects)}")

        # Format current priorities
        priorities_text = ', '.join(context['current_priorities'][:20]) if context['current_priorities'] else 'none'

        return [TextContent(
            type="text",
            text=f"""# Active Context

## Projects ({len(context['projects'])})

{chr(10).join(projects_text) if projects_text else 'No projects found'}

## People ({len(context['people'])})

{chr(10).join(people_text) if people_text else 'No people found'}

## Current Priorities

{priorities_text}

---

Source: ~/.learnbase/active-context/index.md"""
        )]
    except FileNotFoundError as e:
        logger.error(f"Index file not found: {e}")
        return [TextContent(
            type="text",
            text=f"""Error: Active context index not found.

Please create an index.md file at:
~/.learnbase/active-context/index.md

This file should contain:
- Active Projects section with project details
- People section with names and associations
- Current Context section with priorities

See the LearnBase documentation for template and examples."""
        )]
    except Exception as e:
        logger.error(f"Error getting context: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_categorize_task_tool(parser: ContextParser, arguments: Any) -> list[TextContent]:
    """Handle categorize_task tool."""
    text = arguments.get("text")

    if not text:
        return [TextContent(
            type="text",
            text="Error: text is required"
        )]

    try:
        # Match project
        project, project_confidence = parser.match_project(text)

        # Match workspace
        workspace, workspace_confidence = parser.match_workspace(project, text)

        # Detect categories
        categories, categories_confidence = parser.detect_categories(text)

        # Format response
        lines = [
            "# Auto-Categorization Results",
            "",
            f"**Text**: {text}",
            "",
            "## Suggested Categorization",
            "",
            f"**Workspace**: {workspace} (confidence: {workspace_confidence:.0%})",
            f"**Project**: {project or 'none'} (confidence: {project_confidence:.0%})",
            f"**Categories**: {', '.join(categories)} (confidence: {categories_confidence:.0%})",
            "",
            "## Confidence Analysis",
            ""
        ]

        # Add confidence warnings
        if workspace_confidence < 0.6:
            lines.append(f"⚠️ Low confidence for workspace ({workspace_confidence:.0%}) - should ask user")
        else:
            lines.append(f"✓ Good confidence for workspace ({workspace_confidence:.0%})")

        if project and project_confidence < 0.6:
            lines.append(f"⚠️ Low confidence for project ({project_confidence:.0%}) - should ask user")
        elif project:
            lines.append(f"✓ Good confidence for project ({project_confidence:.0%})")

        if categories_confidence < 0.6:
            lines.append(f"⚠️ Low confidence for categories ({categories_confidence:.0%}) - should ask user")
        else:
            lines.append(f"✓ Good confidence for categories ({categories_confidence:.0%})")

        lines.extend([
            "",
            "## Recommended Action",
            ""
        ])

        # Determine if questions should be asked
        should_ask_questions = (
            workspace_confidence < 0.6 or
            (project and project_confidence < 0.6) or
            categories_confidence < 0.6
        )

        if should_ask_questions:
            lines.append("❓ Ask clarifying questions before creating task:")
            if workspace_confidence < 0.6:
                lines.append("  - Which workspace is this for? (work, personal, contract)")
            if project and project_confidence < 0.6:
                lines.append(f"  - Is this for the {project} project?")
            if categories_confidence < 0.6:
                lines.append("  - What type of task is this? (people, idea, project, admin)")
        else:
            lines.append("✓ All confidence scores >= 0.6 - proceed with task creation")

        return [TextContent(
            type="text",
            text="\n".join(lines)
        )]
    except FileNotFoundError:
        return [TextContent(
            type="text",
            text="""Warning: Active context index not found.

Using default categorization (may have lower accuracy).

To improve auto-categorization, create:
~/.learnbase/active-context/index.md"""
        )]
    except Exception as e:
        logger.error(f"Error categorizing task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
