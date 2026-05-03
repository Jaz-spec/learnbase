"""Planning manager for priorities and review workflows."""

import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .database import (
    get_connection, init_db,
    priority_to_row, row_to_priority,
)
from .context_manager import ContextManager
from .tasks_manager import TasksManager

logger = logging.getLogger(__name__)


class PlanningManager:
    """Manages priorities and planning workflows."""

    def __init__(self, context_manager: ContextManager,
                 tasks_manager: TasksManager,
                 reviews_dir: Optional[Path] = None):
        self.context_manager = context_manager
        self.tasks_manager = tasks_manager
        self.conn = context_manager.conn  # reuse same connection
        self.reviews_dir = reviews_dir or (Path.home() / ".learnbase" / "reviews")
        self.reviews_dir.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # Priority CRUD
    # ================================================================

    def create_priority(self, description: str, scope: str, period: str,
                        project_id: Optional[str] = None) -> dict:
        """Create a new priority."""
        slug = self._slugify(description)
        id = f"{scope}-{period}-{slug}"

        priority = priority_to_row({
            "id": id,
            "project_id": project_id,
            "description": description,
            "scope": scope,
            "period": period,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
        })

        try:
            self.conn.execute(
                """INSERT INTO priorities
                   (id, project_id, description, scope, period, status, created_at, completed_at)
                   VALUES (:id, :project_id, :description, :scope, :period, :status, :created_at, :completed_at)""",
                priority,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return priority

    def update_priority(self, id: str, **updates) -> dict:
        """Update a priority. Auto-sets completed_at on completion."""
        row = self.conn.execute(
            "SELECT * FROM priorities WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Priority not found: {id}")

        priority = row_to_priority(row)
        for key, value in updates.items():
            if key in priority and key != "id":
                priority[key] = value

        # Auto-set completed_at
        if updates.get("status") == "completed" and not priority["completed_at"]:
            priority["completed_at"] = datetime.now().isoformat()

        try:
            self.conn.execute(
                """UPDATE priorities SET project_id=:project_id, description=:description,
                   scope=:scope, period=:period, status=:status,
                   created_at=:created_at, completed_at=:completed_at
                   WHERE id=:id""",
                priority,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        return priority

    def get_priority(self, id: str) -> dict:
        """Get a single priority by ID."""
        row = self.conn.execute(
            "SELECT * FROM priorities WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Priority not found: {id}")
        return row_to_priority(row)

    def list_priorities(self, scope: Optional[str] = None,
                        period: Optional[str] = None,
                        status: Optional[str] = None,
                        project_id: Optional[str] = None) -> List[dict]:
        """List priorities with optional filters."""
        query = "SELECT * FROM priorities WHERE 1=1"
        params = []

        if scope:
            query += " AND scope = ?"
            params.append(scope)
        if period:
            query += " AND period = ?"
            params.append(period)
        if status:
            query += " AND status = ?"
            params.append(status)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        query += " ORDER BY created_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [row_to_priority(r) for r in rows]

    # ================================================================
    # Planning Context
    # ================================================================

    def get_planning_context(self, scope: str) -> dict:
        """
        Aggregate all data needed for a planning conversation.

        Args:
            scope: 'monthly' or 'weekly'

        Returns:
            dict with projects, priorities, tasks, stale_priorities, period info
        """
        now = datetime.now()
        current_month = now.strftime("%Y-%m")
        current_week = now.strftime("%Y-W%V")

        # Previous periods
        last_month_dt = now.replace(day=1) - timedelta(days=1)
        last_month = last_month_dt.strftime("%Y-%m")
        last_week_dt = now - timedelta(weeks=1)
        last_week = last_week_dt.strftime("%Y-W%V")

        # Get projects with staleness
        context = self.context_manager.get_context()

        # Get priorities for current and last periods
        monthly_current = self.list_priorities(scope="monthly", period=current_month)
        monthly_last = self.list_priorities(scope="monthly", period=last_month)
        weekly_current = self.list_priorities(scope="weekly", period=current_week)
        weekly_last = self.list_priorities(scope="weekly", period=last_week)

        # Get tasks
        pending_tasks = self.tasks_manager.list_tasks(status="pending")
        in_progress_tasks = self.tasks_manager.list_tasks(status="in_progress")
        overdue_tasks = self.tasks_manager.get_overdue_tasks()

        # Recent completed (last 7 days)
        all_completed = self.tasks_manager.list_tasks(status="completed")
        week_ago = now - timedelta(days=7)
        recent_completed = [
            t for t in all_completed
            if t.completed and t.completed >= week_ago
        ]

        # Stale priorities: past-period priorities still pending
        stale_priorities = []
        for p in self.list_priorities(status="pending"):
            if p["scope"] == "monthly" and p["period"] < current_month:
                stale_priorities.append(p)
            elif p["scope"] == "weekly" and p["period"] < current_week:
                stale_priorities.append(p)

        # Detect gaps
        gaps = {}
        if scope == "weekly":
            if not monthly_current:
                gaps["monthly"] = f"No monthly priorities set for {current_month}"
            if not weekly_last:
                gaps["last_week"] = f"No weekly plan found for {last_week}"
        elif scope == "monthly":
            if not monthly_last:
                gaps["last_month"] = f"No monthly priorities found for {last_month}"

        return {
            "projects": context["projects"],
            "people": context["people"],
            "priorities": {
                "monthly_current": monthly_current,
                "monthly_last": monthly_last,
                "weekly_current": weekly_current,
                "weekly_last": weekly_last,
            },
            "tasks": {
                "pending": [self._task_summary(t) for t in pending_tasks],
                "in_progress": [self._task_summary(t) for t in in_progress_tasks],
                "overdue": [self._task_summary(t) for t in overdue_tasks],
                "recent_completed": [self._task_summary(t) for t in recent_completed],
            },
            "stale_priorities": stale_priorities,
            "gaps": gaps,
            "period": {
                "current_month": current_month,
                "current_week": current_week,
                "last_month": last_month,
                "last_week": last_week,
            },
        }

    # ================================================================
    # Review File Management
    # ================================================================

    def save_review_markdown(self, scope: str, period: str,
                             content: str) -> Path:
        """Save a review summary as markdown."""
        filepath = self.reviews_dir / f"{period}.md"
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved {scope} review: {filepath}")
        return filepath

    # ================================================================
    # Internal
    # ================================================================

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a URL-friendly slug."""
        safe = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', safe).strip('-')
        return slug[:40] if len(slug) > 40 else slug

    @staticmethod
    def _task_summary(task) -> dict:
        """Create a lightweight task summary for planning context."""
        return {
            "id": task.id,
            "title": task.title,
            "workspace": task.workspace,
            "project": task.project,
            "due": task.due.isoformat() if task.due else None,
            "status": task.status,
            "priority_id": task.priority_id,
        }
