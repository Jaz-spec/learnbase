"""Task CRUD operation handlers."""

import logging
from typing import Any
from datetime import datetime
from mcp.types import TextContent

from ..core.tasks_manager import TasksManager
from ..core.models import Task

logger = logging.getLogger(__name__)


def handle_create_task_tool(manager: TasksManager, arguments: Any) -> list[TextContent]:
    """Handle create_task tool."""
    title = arguments.get("title")
    description = arguments.get("description", "")
    due = arguments.get("due")
    categories = arguments.get("categories", [])
    workspace = arguments.get("workspace", "personal")
    project = arguments.get("project")
    confidence = arguments.get("confidence", {})
    reasoning = arguments.get("reasoning")
    priority_id = arguments.get("priority_id")

    if not title or not due:
        return [TextContent(
            type="text",
            text="Error: title and due are required"
        )]

    try:
        # Parse due date
        due_date = datetime.fromisoformat(due)

        # Generate task ID
        task_id = Task.create_id(title, due_date)

        # Create task
        task = Task(
            id=task_id,
            title=title,
            description=description,
            categories=categories if categories else [],
            workspace=workspace,
            project=project,
            due=due_date,
            status='pending',
            confidence=confidence,
            reasoning=reasoning,
            priority_id=priority_id,
        )

        # Set filename
        task.filename = Task.create_filename(task_id)

        # Save task
        created_id = manager.create_task(task)

        # Format confidence scores for display
        confidence_text = "\n".join([
            f"  {k}: {v:.2f}" + (" ✓" if v >= 0.6 else " ⚠️")
            for k, v in confidence.items()
        ]) if confidence else "  None"

        return [TextContent(
            type="text",
            text=f"""✓ Task created: {title}

Details:
- ID: {created_id}
- Due: {due_date.strftime('%Y-%m-%d %H:%M')}
- Workspace: {workspace} ({confidence.get('workspace', 0):.0%} confident)
- Project: {project or 'none'}
- Categories: {', '.join(categories) if categories else 'none'}

Confidence scores:
{confidence_text}

Need any changes? Ask me to update specific fields."""
        )]
    except ValueError as e:
        logger.error(f"Validation error creating task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed creating task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]


def handle_get_task_tool(manager: TasksManager, arguments: Any) -> list[TextContent]:
    """Handle get_task tool."""
    task_id = arguments.get("task_id")

    if not task_id:
        return [TextContent(
            type="text",
            text="Error: task_id is required"
        )]

    try:
        task = manager.get_task(task_id)

        return [TextContent(
            type="text",
            text=f"""# {task.title}

**ID**: {task.id}
**Status**: {task.status}
**Due**: {task.due.strftime('%Y-%m-%d %H:%M')}
**Workspace**: {task.workspace}
**Project**: {task.project or 'none'}
**Categories**: {', '.join(task.categories) if task.categories else 'none'}

**Created**: {task.created.strftime('%Y-%m-%d')}
**Updated**: {task.updated.strftime('%Y-%m-%d')}
{f"**Completed**: {task.completed.strftime('%Y-%m-%d')}" if task.completed else ""}

---

{task.description}"""
        )]
    except ValueError as e:
        logger.error(f"Error getting task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_list_tasks_tool(manager: TasksManager, arguments: Any) -> list[TextContent]:
    """Handle list_tasks tool."""
    status = arguments.get("status")
    workspace = arguments.get("workspace")
    project = arguments.get("project")
    categories = arguments.get("categories")
    due_date = arguments.get("due_date")

    try:
        # Parse due_date if provided
        due_datetime = None
        if due_date:
            due_datetime = datetime.fromisoformat(due_date)

        # Query tasks
        tasks = manager.list_tasks(
            due_date=due_datetime,
            status=status,
            workspace=workspace,
            project=project,
            categories=categories
        )

        if not tasks:
            filter_text = []
            if status:
                filter_text.append(f"status={status}")
            if workspace:
                filter_text.append(f"workspace={workspace}")
            if project:
                filter_text.append(f"project={project}")
            if categories:
                filter_text.append(f"categories={categories}")

            filter_str = ", ".join(filter_text) if filter_text else "no filters"
            return [TextContent(
                type="text",
                text=f"No tasks found ({filter_str})"
            )]

        # Format task list
        lines = [f"Found {len(tasks)} task(s):", ""]

        for task in tasks:
            status_icon = {
                'pending': '⏳',
                'in_progress': '🔄',
                'completed': '✅'
            }.get(task.status, '📋')

            lines.append(f"{status_icon} **{task.title}**")
            lines.append(f"   ID: {task.id}")
            lines.append(f"   Due: {task.due.strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"   Workspace: {task.workspace} | Project: {task.project or 'none'}")
            lines.append(f"   Categories: {', '.join(task.categories) if task.categories else 'none'}")
            lines.append("")

        return [TextContent(
            type="text",
            text="\n".join(lines)
        )]
    except ValueError as e:
        logger.error(f"Error listing tasks: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_update_task_tool(manager: TasksManager, arguments: Any) -> list[TextContent]:
    """Handle update_task tool."""
    task_id = arguments.get("task_id")
    updates = arguments.get("updates", {})

    if not task_id:
        return [TextContent(
            type="text",
            text="Error: task_id is required"
        )]

    if not updates:
        return [TextContent(
            type="text",
            text="Error: updates dictionary is required"
        )]

    try:
        # Parse datetime fields in updates
        if 'due' in updates:
            updates['due'] = datetime.fromisoformat(updates['due'])
        if 'completed' in updates and updates['completed']:
            updates['completed'] = datetime.fromisoformat(updates['completed'])

        # Update task
        task = manager.update_task(task_id, updates)

        # Format updated fields
        updated_fields = [f"- {k}: {v}" for k, v in updates.items()]

        return [TextContent(
            type="text",
            text=f"""✓ Task updated: {task.title}

Updated fields:
{chr(10).join(updated_fields)}

Current status:
- Status: {task.status}
- Due: {task.due.strftime('%Y-%m-%d %H:%M')}
- Updated: {task.updated.strftime('%Y-%m-%d %H:%M')}"""
        )]
    except ValueError as e:
        logger.error(f"Error updating task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed updating task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]


def handle_archive_task_tool(manager: TasksManager, arguments: Any) -> list[TextContent]:
    """Handle archive_task tool."""
    task_id = arguments.get("task_id")

    if not task_id:
        return [TextContent(
            type="text",
            text="Error: task_id is required"
        )]

    try:
        manager.archive_task(task_id)

        return [TextContent(
            type="text",
            text=f"✓ Task archived: {task_id}"
        )]
    except ValueError as e:
        logger.error(f"Error archiving task: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
