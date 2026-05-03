"""Planning and priority tool handlers."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.planning_manager import PlanningManager

logger = logging.getLogger(__name__)


def handle_get_priorities_tool(manager: PlanningManager, arguments: Any) -> list[TextContent]:
    """Handle get_priorities tool."""
    try:
        priorities = manager.list_priorities(
            scope=arguments.get("scope"),
            period=arguments.get("period"),
            status=arguments.get("status"),
            project_id=arguments.get("project_id"),
        )

        if not priorities:
            return [TextContent(type="text", text="No priorities found matching filters.")]

        lines = [f"# Priorities ({len(priorities)})\n"]
        for p in priorities:
            status_icon = {
                "pending": "\u23f3",
                "in_progress": "\u25b6\ufe0f",
                "completed": "\u2705",
                "rolled_over": "\u27a1\ufe0f",
            }.get(p["status"], "")

            line = f"{status_icon} **{p['description']}**"
            line += f"\n  Scope: {p['scope']} | Period: {p['period']} | Status: {p['status']}"
            if p["project_id"]:
                line += f" | Project: {p['project_id']}"
            lines.append(line)

        return [TextContent(type="text", text="\n\n".join(lines))]
    except Exception as e:
        logger.error(f"Error getting priorities: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_create_priority_tool(manager: PlanningManager, arguments: Any) -> list[TextContent]:
    """Handle create_priority tool."""
    description = arguments.get("description")
    scope = arguments.get("scope")
    period = arguments.get("period")

    if not all([description, scope, period]):
        return [TextContent(type="text", text="Error: description, scope, and period are required")]

    try:
        priority = manager.create_priority(
            description=description,
            scope=scope,
            period=period,
            project_id=arguments.get("project_id"),
        )
        return [TextContent(
            type="text",
            text=f"Priority created: **{priority['description']}**\n\n"
                 f"ID: `{priority['id']}`\n"
                 f"Scope: {priority['scope']} | Period: {priority['period']}\n"
                 f"Project: {priority['project_id'] or 'none'}"
        )]
    except Exception as e:
        logger.error(f"Error creating priority: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_update_priority_tool(manager: PlanningManager, arguments: Any) -> list[TextContent]:
    """Handle update_priority tool."""
    id = arguments.get("id")
    if not id:
        return [TextContent(type="text", text="Error: id is required")]

    updates = {}
    for key in ("description", "status", "project_id"):
        if arguments.get(key) is not None:
            updates[key] = arguments[key]

    try:
        priority = manager.update_priority(id, **updates)
        return [TextContent(
            type="text",
            text=f"Priority updated: **{priority['description']}**\n\n"
                 f"Status: {priority['status']}"
                 + (f"\nCompleted: {priority['completed_at']}" if priority["completed_at"] else "")
        )]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {e}")]
    except Exception as e:
        logger.error(f"Error updating priority: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_get_planning_context_tool(manager: PlanningManager, arguments: Any) -> list[TextContent]:
    """Handle get_planning_context tool."""
    scope = arguments.get("scope")
    if not scope:
        return [TextContent(type="text", text="Error: scope is required ('monthly' or 'weekly')")]

    try:
        ctx = manager.get_planning_context(scope)

        lines = [f"# Planning Context ({scope.title()})\n"]

        # Period info
        period = ctx["period"]
        lines.append(f"**Current month:** {period['current_month']} | "
                      f"**Current week:** {period['current_week']}\n")

        # Gaps / warnings
        if ctx["gaps"]:
            lines.append("## Gaps\n")
            for key, msg in ctx["gaps"].items():
                lines.append(f"\u26a0\ufe0f {msg}")
            lines.append("")

        # Projects
        lines.append(f"## Projects ({len(ctx['projects'])})\n")
        for p in ctx["projects"]:
            staleness = f" **[{p['staleness'].upper()}]**" if p["staleness"] != "fresh" else ""
            lines.append(f"- **{p['name']}** ({p['workspace']}){staleness}: {p['description']}")
        if not ctx["projects"]:
            lines.append("No projects configured.")
        lines.append("")

        # Monthly priorities
        mp = ctx["priorities"]
        if scope == "weekly":
            lines.append(f"## Monthly Priorities ({period['current_month']})\n")
            if mp["monthly_current"]:
                for p in mp["monthly_current"]:
                    lines.append(f"- [{p['status']}] {p['description']}")
            else:
                lines.append("No monthly priorities set for this month.")
            lines.append("")

        # Last period priorities + outcomes
        if scope == "monthly" and mp["monthly_last"]:
            lines.append(f"## Last Month's Priorities ({period['last_month']})\n")
            for p in mp["monthly_last"]:
                lines.append(f"- [{p['status']}] {p['description']}")
            lines.append("")

        if scope == "weekly" and mp["weekly_last"]:
            lines.append(f"## Last Week's Priorities ({period['last_week']})\n")
            for p in mp["weekly_last"]:
                lines.append(f"- [{p['status']}] {p['description']}")
            lines.append("")

        # Stale priorities
        if ctx["stale_priorities"]:
            lines.append(f"## Stale Priorities ({len(ctx['stale_priorities'])})\n")
            for p in ctx["stale_priorities"]:
                lines.append(f"- [{p['scope']}/{p['period']}] {p['description']} ({p['status']})")
            lines.append("")

        # Tasks summary
        tasks = ctx["tasks"]
        lines.append("## Tasks\n")
        lines.append(f"- Overdue: {len(tasks['overdue'])}")
        lines.append(f"- In progress: {len(tasks['in_progress'])}")
        lines.append(f"- Pending: {len(tasks['pending'])}")
        lines.append(f"- Completed (last 7 days): {len(tasks['recent_completed'])}")
        lines.append("")

        if tasks["overdue"]:
            lines.append("### Overdue\n")
            for t in tasks["overdue"]:
                lines.append(f"- **{t['title']}** ({t['workspace']}) - due {t['due'][:10]}")
            lines.append("")

        if tasks["in_progress"]:
            lines.append("### In Progress\n")
            for t in tasks["in_progress"]:
                lines.append(f"- **{t['title']}** ({t['workspace']})")
            lines.append("")

        # People
        if ctx["people"]:
            lines.append(f"## People ({len(ctx['people'])})\n")
            for p in ctx["people"]:
                lines.append(f"- **{p['name']}**: {p['relationship']}")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        logger.error(f"Error getting planning context: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


def handle_save_review_tool(manager: PlanningManager, arguments: Any) -> list[TextContent]:
    """Handle save_review tool."""
    scope = arguments.get("scope")
    period = arguments.get("period")
    content = arguments.get("content")

    if not all([scope, period, content]):
        return [TextContent(type="text", text="Error: scope, period, and content are required")]

    try:
        filepath = manager.save_review_markdown(scope, period, content)
        return [TextContent(
            type="text",
            text=f"Review saved: {filepath}\n\n"
                 f"Scope: {scope} | Period: {period}"
        )]
    except Exception as e:
        logger.error(f"Error saving review: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]
