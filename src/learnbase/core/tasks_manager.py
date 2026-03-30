"""Task manager backed by SQLite."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from .models import Task
from .database import get_connection, init_db, task_to_row, row_to_task

logger = logging.getLogger(__name__)


class TasksManager:
    """Manages tasks in SQLite (~/.learnbase/tasks.db)."""

    def __init__(self, db_path: Optional[Path] = None):
        self.conn = get_connection(db_path)
        init_db(self.conn)

    # ----------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------

    def _validate_task_id(self, task_id: str) -> None:
        if not task_id:
            raise ValueError("Task ID cannot be empty")
        if not all(c.isalnum() or c in '-' for c in task_id):
            raise ValueError(
                f"Task ID contains invalid characters: '{task_id}'. "
                f"Only alphanumeric and hyphens allowed."
            )

    # ----------------------------------------------------------------
    # CRUD Operations
    # ----------------------------------------------------------------

    def create_task(self, task: Task) -> str:
        """Create a task. Returns the task ID."""
        self._validate_task_id(task.id)

        if not task.filename:
            task.filename = Task.create_filename(task.id)

        row = task_to_row(task)
        try:
            self.conn.execute(
                """INSERT INTO tasks
                   (id, title, description, categories, workspace, project,
                    due, status, dependencies, created, updated, completed,
                    confidence, reasoning, archived)
                   VALUES
                   (:id, :title, :description, :categories, :workspace, :project,
                    :due, :status, :dependencies, :created, :updated, :completed,
                    :confidence, :reasoning, :archived)""",
                row,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        logger.info(f"Created task: {task.id}")
        return task.id

    def get_task(self, task_id: str) -> Task:
        """Load task by ID (non-archived only)."""
        self._validate_task_id(task_id)
        cur = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND archived = 0", (task_id,)
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Task not found: {task_id}")
        return row_to_task(row)

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update task fields and return the updated task."""
        task = self.get_task(task_id)

        for field, value in updates.items():
            if not hasattr(task, field):
                raise ValueError(f"Invalid task field: {field}")
            setattr(task, field, value)

        task.updated = datetime.now()

        if updates.get('status') == 'completed' and task.completed is None:
            task.completed = datetime.now()

        row = task_to_row(task)
        try:
            self.conn.execute(
                """UPDATE tasks SET
                   title=:title, description=:description, categories=:categories,
                   workspace=:workspace, project=:project, due=:due, status=:status,
                   dependencies=:dependencies, created=:created, updated=:updated,
                   completed=:completed, confidence=:confidence, reasoning=:reasoning,
                   archived=:archived
                   WHERE id=:id""",
                row,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        logger.info(f"Updated task: {task_id}")
        return task

    def delete_task(self, task_id: str) -> None:
        """Soft-delete (archive) a task."""
        self._validate_task_id(task_id)
        cur = self.conn.execute(
            "UPDATE tasks SET archived = 1 WHERE id = ? AND archived = 0",
            (task_id,),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"Task not found: {task_id}")
        logger.info(f"Archived task: {task_id}")

    # ----------------------------------------------------------------
    # Query Operations
    # ----------------------------------------------------------------

    def list_tasks(
        self,
        due_date: Optional[datetime] = None,
        status: Optional[str] = None,
        workspace: Optional[str] = None,
        project: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Task]:
        """List non-archived tasks matching filters."""
        clauses = ["archived = 0"]
        params: list = []

        if due_date:
            clauses.append("date(due) = date(?)")
            params.append(due_date.isoformat())
        if status:
            clauses.append("status = ?")
            params.append(status)
        if workspace:
            clauses.append("workspace = ?")
            params.append(workspace)
        if project:
            clauses.append("project = ?")
            params.append(project)

        where = " AND ".join(clauses)
        cur = self.conn.execute(
            f"SELECT * FROM tasks WHERE {where} ORDER BY due", params
        )
        tasks = [row_to_task(r) for r in cur.fetchall()]

        # Category filtering in Python (JSON column)
        if categories:
            tasks = [
                t for t in tasks
                if all(cat in t.categories for cat in categories)
            ]

        return tasks

    def get_overdue_tasks(self) -> List[Task]:
        """Get non-archived tasks past due that are pending or in_progress."""
        now = datetime.now().isoformat()
        cur = self.conn.execute(
            """SELECT * FROM tasks
               WHERE archived = 0
                 AND due < ?
                 AND status IN ('pending', 'in_progress')
               ORDER BY due""",
            (now,),
        )
        return [row_to_task(r) for r in cur.fetchall()]

    def get_tasks_due_today(self) -> List[Task]:
        """Get non-archived tasks due today that are pending or in_progress."""
        today = datetime.now().strftime("%Y-%m-%d")
        cur = self.conn.execute(
            """SELECT * FROM tasks
               WHERE archived = 0
                 AND date(due) = ?
                 AND status IN ('pending', 'in_progress')
               ORDER BY due""",
            (today,),
        )
        return [row_to_task(r) for r in cur.fetchall()]

    def get_tasks_this_week(self) -> List[Task]:
        """Get non-archived tasks due within 7 days (from today onwards)."""
        today = datetime.now().strftime("%Y-%m-%d")
        week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        cur = self.conn.execute(
            """SELECT * FROM tasks
               WHERE archived = 0
                 AND date(due) >= ?
                 AND date(due) <= ?
                 AND status IN ('pending', 'in_progress')
               ORDER BY due""",
            (today, week),
        )
        return [row_to_task(r) for r in cur.fetchall()]

    # ----------------------------------------------------------------
    # Archive Operations
    # ----------------------------------------------------------------

    def archive_task(self, task_id: str) -> None:
        """Archive a completed task."""
        task = self.get_task(task_id)
        if task.status != 'completed':
            raise ValueError(f"Can only archive completed tasks: {task_id}")
        self.delete_task(task_id)
