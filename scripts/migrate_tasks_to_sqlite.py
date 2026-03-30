#!/usr/bin/env python3
"""Migrate existing markdown task files into SQLite."""

import sys
from pathlib import Path

# Add src to path so we can import learnbase
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from learnbase.core.models import Task
from learnbase.core.database import get_connection, init_db, task_to_row

TASKS_DIR = Path.home() / ".learnbase" / "tasks"
ARCHIVE_DIR = TASKS_DIR / "archive"


def migrate():
    conn = get_connection()
    init_db(conn)

    inserted = 0
    skipped = 0
    errors = []

    sources = []
    # Active tasks
    if TASKS_DIR.exists():
        sources.extend((f, False) for f in sorted(TASKS_DIR.glob("*.md")))
    # Archived tasks
    if ARCHIVE_DIR.exists():
        sources.extend((f, True) for f in sorted(ARCHIVE_DIR.glob("*.md")))

    print(f"Found {len(sources)} markdown task files")

    for filepath, is_archived in sources:
        try:
            task = Task.from_markdown_file(filepath)
            row = task_to_row(task)
            if is_archived:
                row["archived"] = 1
            conn.execute(
                """INSERT OR IGNORE INTO tasks
                   (id, title, description, categories, workspace, project,
                    due, status, dependencies, created, updated, completed,
                    confidence, reasoning, archived)
                   VALUES
                   (:id, :title, :description, :categories, :workspace, :project,
                    :due, :status, :dependencies, :created, :updated, :completed,
                    :confidence, :reasoning, :archived)""",
                row,
            )
            if conn.execute("SELECT changes()").fetchone()[0] > 0:
                inserted += 1
                label = " (archived)" if is_archived else ""
                print(f"  + {task.id}{label}")
            else:
                skipped += 1
        except Exception as e:
            errors.append((filepath.name, str(e)))
            print(f"  ! Error: {filepath.name}: {e}")

    conn.commit()
    conn.close()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (already exist)")
    if errors:
        print(f"{len(errors)} errors:")
        for name, err in errors:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    migrate()
