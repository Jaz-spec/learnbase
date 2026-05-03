#!/usr/bin/env python3
"""One-time migration: parse active-context/index.md into SQLite."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.learnbase.core.context_manager import ContextManager


def migrate():
    """Parse index.md and insert projects + people into the database."""
    manager = ContextManager()

    # Projects from index.md (last updated 2026-02-06)
    projects = [
        {
            "id": "learnbase",
            "name": "LearnBase",
            "workspace": "personal",
            "description": (
                "MCP server for spaced repetition, task management, "
                "and AI-driven learning workflows."
            ),
        },
        {
            "id": "distribution",
            "name": "Distribution",
            "workspace": "work",
            "description": (
                "Full-stack dashboard for email automation, outreach tracking, "
                "and workshop campaigns at FAC."
            ),
        },
    ]

    # People from index.md
    people = [
        {"id": "dan", "name": "Dan", "relationship": "CEO of company I work for"},
        {"id": "izaak", "name": "Izaak", "relationship": "CTO, focuses on course curriculum"},
        {"id": "jason", "name": "Jason", "relationship": "co-worker, apprentice portfolio project"},
        {"id": "jess", "name": "Jess", "relationship": "ops, admin, learner welfare and logistics"},
    ]

    print("Migrating active context to SQLite...\n")

    # Insert projects
    for p in projects:
        try:
            manager.add_project(p["id"], p["name"], p["workspace"], p["description"])
            print(f"  Added project: {p['name']} ({p['workspace']})")
        except Exception as e:
            print(f"  Skipped project {p['id']}: {e}")

    # Backdate updated_at to 2026-02-06 so they show as STALE immediately
    manager.conn.execute(
        "UPDATE projects SET updated_at = '2026-02-06T00:00:00'"
    )
    manager.conn.commit()
    print("\n  Set updated_at to 2026-02-06 (will appear as STALE)")

    # Insert people
    for p in people:
        try:
            manager.add_person(p["id"], p["name"], p["relationship"])
            print(f"  Added person: {p['name']} - {p['relationship']}")
        except Exception as e:
            print(f"  Skipped person {p['id']}: {e}")

    print("\nMigration complete!")
    print(f"Database: {Path.home() / '.learnbase' / 'tasks.db'}")
    print("\nVerify with:")
    print("  sqlite3 ~/.learnbase/tasks.db 'SELECT * FROM projects;'")
    print("  sqlite3 ~/.learnbase/tasks.db 'SELECT * FROM people;'")


if __name__ == "__main__":
    migrate()
