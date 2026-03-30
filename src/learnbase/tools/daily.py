"""Daily workflow operation handlers."""

import logging
from typing import Any
from datetime import datetime
from mcp.types import TextContent

from ..core.daily_manager import DailyManager

logger = logging.getLogger(__name__)


def handle_create_daily_plan_tool(manager: DailyManager, arguments: Any) -> list[TextContent]:
    """Handle create_daily_plan tool."""
    date_str = arguments.get("date")

    try:
        # Parse date if provided, otherwise use today
        date = datetime.fromisoformat(date_str) if date_str else datetime.now()

        # Create daily plan
        filepath = manager.create_daily_plan(date)

        # Get counts
        daily_log = manager.get_daily_log(date)

        overdue_count = len(daily_log.tasks_overdue)
        today_count = len(daily_log.tasks_due_today)
        week_count = len(daily_log.tasks_this_week)

        return [TextContent(
            type="text",
            text=f"""✓ Daily plan created: {date.strftime('%A, %Y-%m-%d')}

📋 Today's Tasks:
  🔴 {overdue_count} overdue
  ⏰ {today_count} due today
  📅 {week_count} this week

Top priorities:
{chr(10).join([f"{i+1}. {task_id}" for i, task_id in enumerate(daily_log.priorities[:5])])}

Daily plan: ~/.learnbase/daily/{date.strftime('%Y-%m-%d')}.md

Ready to tackle these? Let me know if you need to:
- Reschedule any tasks
- Add new tasks
- See more details on a specific task"""
        )]
    except ValueError as e:
        logger.error(f"Error creating daily plan: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed creating daily plan: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]


def handle_update_daily_reflection_tool(manager: DailyManager, arguments: Any) -> list[TextContent]:
    """Handle update_daily_reflection tool."""
    date_str = arguments.get("date")
    completed = arguments.get("completed", [])
    incomplete = arguments.get("incomplete", [])
    new_tasks = arguments.get("new_tasks", [])
    reflection_notes = arguments.get("reflection_notes")

    if not date_str:
        return [TextContent(
            type="text",
            text="Error: date is required"
        )]

    try:
        # Parse date
        date = datetime.fromisoformat(date_str)

        # Update reflection
        filepath = manager.update_reflection(
            date=date,
            completed=completed,
            incomplete=incomplete,
            new_tasks=new_tasks,
            notes=reflection_notes
        )

        # Format summary
        completed_count = len(completed)
        incomplete_count = len(incomplete)
        rollover_count = sum(1 for item in incomplete if item.get('rollover', False))

        summary_lines = [
            f"✓ Day wrapped up! ({date.strftime('%Y-%m-%d')})",
            "",
            "Summary:",
            f"- {completed_count} tasks completed",
            f"- {rollover_count} tasks rolled to tomorrow",
            f"- {len(new_tasks)} new follow-up tasks created",
            ""
        ]

        if completed:
            summary_lines.append("Completed tasks:")
            for item in completed:
                task_id = item.get('task_id', '')
                summary_lines.append(f"  ✓ {task_id}")
            summary_lines.append("")

        if incomplete:
            summary_lines.append("Incomplete tasks:")
            for item in incomplete:
                task_id = item.get('task_id', '')
                rollover = item.get('rollover', False)
                action = "rolled to tomorrow" if rollover else "still pending"
                summary_lines.append(f"  ⏭️ {task_id} ({action})")
            summary_lines.append("")

        if new_tasks:
            summary_lines.append("New follow-up tasks:")
            for task_id in new_tasks:
                summary_lines.append(f"  + {task_id}")
            summary_lines.append("")

        summary_lines.append("Tasks updated and daily file deleted.")
        summary_lines.append("")
        summary_lines.append("Great work today! 🎉")

        return [TextContent(
            type="text",
            text="\n".join(summary_lines)
        )]
    except ValueError as e:
        logger.error(f"Error updating daily reflection: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
    except (IOError, OSError) as e:
        logger.error(f"File operation failed updating daily reflection: {e}")
        return [TextContent(
            type="text",
            text=f"Error: File operation failed: {e}"
        )]
