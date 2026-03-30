"""SQLite database connection and helpers for task storage."""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import Task

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".learnbase" / "tasks.db"

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    categories TEXT NOT NULL DEFAULT '[]',
    workspace TEXT NOT NULL DEFAULT 'personal',
    project TEXT,
    due TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    dependencies TEXT NOT NULL DEFAULT '[]',
    created TEXT NOT NULL,
    updated TEXT NOT NULL,
    completed TEXT,
    confidence TEXT NOT NULL DEFAULT '{}',
    reasoning TEXT,
    archived INTEGER NOT NULL DEFAULT 0
);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a SQLite connection with WAL mode and busy timeout."""
    if db_path is None:
        db_path = DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the tasks table if it doesn't exist."""
    conn.execute(CREATE_TASKS_TABLE)
    conn.commit()
    logger.debug("Initialized tasks database")


def task_to_row(task: Task) -> dict:
    """Serialize a Task dataclass to a dict suitable for INSERT/UPDATE."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "categories": json.dumps(task.categories),
        "workspace": task.workspace,
        "project": task.project,
        "due": task.due.isoformat(),
        "status": task.status,
        "dependencies": json.dumps(task.dependencies),
        "created": task.created.isoformat(),
        "updated": task.updated.isoformat(),
        "completed": task.completed.isoformat() if task.completed else None,
        "confidence": json.dumps(task.confidence),
        "reasoning": task.reasoning,
        "archived": 0,
    }


def row_to_task(row: sqlite3.Row) -> Task:
    """Deserialize a database row to a Task dataclass."""
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        categories=json.loads(row["categories"]),
        workspace=row["workspace"],
        project=row["project"],
        due=datetime.fromisoformat(row["due"]),
        status=row["status"],
        dependencies=json.loads(row["dependencies"]),
        created=datetime.fromisoformat(row["created"]),
        updated=datetime.fromisoformat(row["updated"]),
        completed=datetime.fromisoformat(row["completed"]) if row["completed"] else None,
        confidence=json.loads(row["confidence"]),
        reasoning=row["reasoning"],
        filename=Task.create_filename(row["id"]),
    )
