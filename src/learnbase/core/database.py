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

CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workspace TEXT NOT NULL CHECK(workspace IN ('work', 'personal', 'contract')),
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
    updated_at TEXT NOT NULL
);
"""

CREATE_PEOPLE_TABLE = """
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relationship TEXT NOT NULL
);
"""

CREATE_PRIORITIES_TABLE = """
CREATE TABLE IF NOT EXISTS priorities (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    description TEXT NOT NULL,
    scope TEXT NOT NULL CHECK(scope IN ('monthly', 'weekly')),
    period TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'in_progress', 'completed', 'rolled_over')),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
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
    """Create all tables if they don't exist."""
    conn.execute(CREATE_TASKS_TABLE)
    conn.execute(CREATE_PROJECTS_TABLE)
    conn.execute(CREATE_PEOPLE_TABLE)
    conn.execute(CREATE_PRIORITIES_TABLE)
    _ensure_priority_id_column(conn)
    _ensure_pinned_column(conn)
    conn.commit()
    logger.debug("Initialized database")


def _ensure_priority_id_column(conn: sqlite3.Connection) -> None:
    """Add priority_id column to tasks if it doesn't exist."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if 'priority_id' not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN priority_id TEXT")
        logger.debug("Added priority_id column to tasks table")


def _ensure_pinned_column(conn: sqlite3.Connection) -> None:
    """Add pinned column to tasks if it doesn't exist."""
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if 'pinned' not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        logger.debug("Added pinned column to tasks table")


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
        "priority_id": task.priority_id,
        "pinned": 1 if task.pinned else 0,
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
        priority_id=row["priority_id"] if "priority_id" in row.keys() else None,
        pinned=bool(row["pinned"]) if "pinned" in row.keys() else False,
        filename=Task.create_filename(row["id"]),
    )


def project_to_row(project: dict) -> dict:
    """Serialize a project dict for INSERT/UPDATE."""
    return {
        "id": project["id"],
        "name": project["name"],
        "workspace": project["workspace"],
        "description": project["description"],
        "status": project.get("status", "active"),
        "updated_at": project.get("updated_at", datetime.now().isoformat()),
    }


def row_to_project(row: sqlite3.Row) -> dict:
    """Deserialize a database row to a project dict."""
    return {
        "id": row["id"],
        "name": row["name"],
        "workspace": row["workspace"],
        "description": row["description"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    }


def person_to_row(person: dict) -> dict:
    """Serialize a person dict for INSERT/UPDATE."""
    return {
        "id": person["id"],
        "name": person["name"],
        "relationship": person["relationship"],
    }


def row_to_person(row: sqlite3.Row) -> dict:
    """Deserialize a database row to a person dict."""
    return {
        "id": row["id"],
        "name": row["name"],
        "relationship": row["relationship"],
    }


def priority_to_row(priority: dict) -> dict:
    """Serialize a priority dict for INSERT/UPDATE."""
    return {
        "id": priority["id"],
        "project_id": priority.get("project_id"),
        "description": priority["description"],
        "scope": priority["scope"],
        "period": priority["period"],
        "status": priority.get("status", "pending"),
        "created_at": priority.get("created_at", datetime.now().isoformat()),
        "completed_at": priority.get("completed_at"),
    }


def row_to_priority(row: sqlite3.Row) -> dict:
    """Deserialize a database row to a priority dict."""
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "description": row["description"],
        "scope": row["scope"],
        "period": row["period"],
        "status": row["status"],
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }
