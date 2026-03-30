"""Daily workflow manager for task management."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

from .models import DailyLog, Task
from .tasks_manager import TasksManager

logger = logging.getLogger(__name__)


class DailyManager:
    """Manage daily logs in ~/.learnbase/daily/"""

    def __init__(self, tasks_manager: TasksManager, daily_dir: Optional[Path] = None):
        """
        Initialize DailyManager.

        Args:
            tasks_manager: TasksManager instance for querying tasks
            daily_dir: Directory to store daily logs (default: ~/.learnbase/daily)
        """
        if daily_dir is None:
            daily_dir = Path.home() / ".learnbase" / "daily"

        self.daily_dir = Path(daily_dir)
        self.tasks_manager = tasks_manager
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create daily directory if it doesn't exist."""
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured daily directory exists: {self.daily_dir}")

    def _get_daily_filepath(self, date: datetime) -> Path:
        """
        Get filepath for daily log.

        Args:
            date: Date for daily log

        Returns:
            Path to daily log file
        """
        date_str = date.strftime('%Y-%m-%d')
        return self.daily_dir / f"{date_str}.md"

    def _save_daily_log(self, daily_log: DailyLog, filepath: Path) -> None:
        """
        Save daily log to file with atomic write.

        Args:
            daily_log: DailyLog instance to save
            filepath: Full path where daily log should be saved

        Raises:
            IOError: If file cannot be written
        """
        try:
            # Atomic write: write to temp file, then rename
            temp_path = filepath.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(daily_log.to_markdown_file())

            # Atomic rename
            temp_path.replace(filepath)
            logger.debug(f"Saved daily log to {filepath.name}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to save daily log {filepath.name}: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to save daily log {filepath.name}: {e}") from e

    # ================================================================
    # Daily Plan Operations
    # ================================================================

    def create_daily_plan(self, date: Optional[datetime] = None) -> Path:
        """
        Generate morning checklist from tasks.

        Args:
            date: Date for daily plan (default: today)

        Returns:
            Path to created daily log file

        Raises:
            ValueError: If daily plan already exists for date
        """
        if date is None:
            date = datetime.now()

        filepath = self._get_daily_filepath(date)

        # Check if daily plan already exists
        if filepath.exists():
            raise ValueError(f"Daily plan already exists for {date.strftime('%Y-%m-%d')}")

        # Query tasks
        overdue_tasks = self.tasks_manager.get_overdue_tasks()
        tasks_due_today = self.tasks_manager.get_tasks_due_today()
        tasks_this_week = self.tasks_manager.get_tasks_this_week()

        # Create daily log
        daily_log = DailyLog(
            date=date,
            tasks_overdue=[task.id for task in overdue_tasks],
            tasks_due_today=[task.id for task in tasks_due_today],
            tasks_this_week=[task.id for task in tasks_this_week],
            priorities=self._calculate_priorities(overdue_tasks, tasks_due_today, tasks_this_week)
        )

        # Save daily log
        self._save_daily_log(daily_log, filepath)
        logger.info(f"Created daily plan for {date.strftime('%Y-%m-%d')}")

        return filepath

    def _calculate_priorities(
        self,
        overdue: List[Task],
        due_today: List[Task],
        this_week: List[Task]
    ) -> List[str]:
        """
        Calculate task priorities based on due date, workspace, and dependencies.

        Args:
            overdue: Overdue tasks
            due_today: Tasks due today
            this_week: Tasks due this week

        Returns:
            Ordered list of task IDs (highest priority first)
        """
        priorities = []

        # Priority 1: Overdue tasks (by due date, oldest first)
        overdue_sorted = sorted(overdue, key=lambda t: t.due)
        priorities.extend([task.id for task in overdue_sorted])

        # Priority 2: Tasks due today (by workspace priority: work > contract > personal)
        workspace_priority = {'work': 1, 'contract': 2, 'personal': 3}
        due_today_sorted = sorted(
            due_today,
            key=lambda t: (workspace_priority.get(t.workspace, 4), t.due)
        )
        priorities.extend([task.id for task in due_today_sorted])

        # Priority 3: Tasks this week (by due date)
        this_week_sorted = sorted(this_week, key=lambda t: t.due)
        priorities.extend([task.id for task in this_week_sorted])

        # Remove duplicates while preserving order
        seen = set()
        unique_priorities = []
        for task_id in priorities:
            if task_id not in seen:
                seen.add(task_id)
                unique_priorities.append(task_id)

        return unique_priorities

    # ================================================================
    # Daily Log Operations
    # ================================================================

    def get_daily_log(self, date: Optional[datetime] = None) -> Optional[DailyLog]:
        """
        Load existing daily log.

        Args:
            date: Date for daily log (default: today)

        Returns:
            DailyLog instance if exists, None otherwise
        """
        if date is None:
            date = datetime.now()

        filepath = self._get_daily_filepath(date)

        if not filepath.exists():
            return None

        return DailyLog.from_markdown_file(filepath)

    def update_reflection(
        self,
        date: datetime,
        completed: List[Dict[str, Any]],
        incomplete: List[Dict[str, Any]],
        new_tasks: List[str],
        notes: Optional[str] = None
    ) -> Path:
        """
        Add evening reflection to daily log.

        Args:
            date: Date for daily log
            completed: List of completed tasks with notes [{task_id, notes}, ...]
            incomplete: List of incomplete tasks [{task_id, reason, rollover}, ...]
            new_tasks: List of new task IDs created during reflection
            notes: General reflection notes

        Returns:
            Path to updated daily log file

        Note: This method updates task files and deletes the daily log after processing.
        """
        filepath = self._get_daily_filepath(date)

        if not filepath.exists():
            raise ValueError(f"Daily log not found for {date.strftime('%Y-%m-%d')}")

        # Load existing daily log
        daily_log = DailyLog.from_markdown_file(filepath)

        # Update daily log with reflection data
        daily_log.completed = completed
        daily_log.incomplete = incomplete
        daily_log.new_tasks = new_tasks
        daily_log.reflection_notes = notes

        # Process completed tasks
        for item in completed:
            task_id = item.get('task_id')
            task_notes = item.get('notes', '')

            if task_id:
                self._update_task_from_reflection(task_id, task_notes, status='completed')

        # Process incomplete tasks
        for item in incomplete:
            task_id = item.get('task_id')
            reason = item.get('reason', '')
            rollover = item.get('rollover', False)

            if task_id and rollover:
                # Roll over task to tomorrow
                self._rollover_task(task_id, reason)

        # Save updated daily log temporarily (for user review if needed)
        self._save_daily_log(daily_log, filepath)
        logger.info(f"Updated daily reflection for {date.strftime('%Y-%m-%d')}")

        # Delete daily log after processing (as per design decision)
        filepath.unlink()
        logger.info(f"Deleted daily log for {date.strftime('%Y-%m-%d')}")

        return filepath

    def _update_task_from_reflection(
        self,
        task_id: str,
        notes: str,
        status: Optional[str] = None
    ) -> None:
        """
        Append reflection notes to task description and optionally update status.

        Args:
            task_id: Task ID
            notes: Reflection notes to append
            status: Optional new status
        """
        try:
            task = self.tasks_manager.get_task(task_id)

            # Append notes to description
            if notes:
                task.description += f"\n\n## Reflection Notes ({datetime.now().strftime('%Y-%m-%d')})\n\n{notes}"

            # Update status if provided
            updates = {'description': task.description}
            if status:
                updates['status'] = status

            self.tasks_manager.update_task(task_id, updates)
            logger.info(f"Updated task from reflection: {task_id}")
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            raise

    def _rollover_task(self, task_id: str, reason: str) -> None:
        """
        Roll over task to tomorrow by updating due date.

        Args:
            task_id: Task ID
            reason: Reason for rollover
        """
        try:
            task = self.tasks_manager.get_task(task_id)

            # Add rollover note
            rollover_note = f"\n\n## Rolled Over ({datetime.now().strftime('%Y-%m-%d')})\n\nReason: {reason}"
            task.description += rollover_note

            # Update due date to tomorrow
            from datetime import timedelta
            tomorrow = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            tomorrow += timedelta(days=1)

            updates = {
                'description': task.description,
                'due': tomorrow
            }

            self.tasks_manager.update_task(task_id, updates)
            logger.info(f"Rolled over task to tomorrow: {task_id}")
        except Exception as e:
            logger.error(f"Error rolling over task {task_id}: {e}")
            raise
