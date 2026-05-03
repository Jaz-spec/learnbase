"""SQLite-backed context management for projects and people."""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .database import (
    get_connection, init_db,
    project_to_row, row_to_project,
    person_to_row, row_to_person,
)

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages project and people context in SQLite for task categorization."""

    STALENESS_THRESHOLD_DAYS = 14

    def __init__(self, db_path: Optional[Path] = None):
        self.conn = get_connection(db_path)
        init_db(self.conn)

    # ================================================================
    # Project CRUD
    # ================================================================

    def add_project(self, id: str, name: str, workspace: str,
                    description: str) -> dict:
        """Add a new project."""
        project = project_to_row({
            "id": id,
            "name": name,
            "workspace": workspace,
            "description": description,
            "status": "active",
            "updated_at": datetime.now().isoformat(),
        })
        try:
            self.conn.execute(
                """INSERT INTO projects (id, name, workspace, description, status, updated_at)
                   VALUES (:id, :name, :workspace, :description, :status, :updated_at)""",
                project,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self._annotate_staleness(project)

    def update_project(self, id: str, **updates) -> dict:
        """Update a project. Always touches updated_at."""
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Project not found: {id}")

        project = row_to_project(row)
        for key, value in updates.items():
            if key in project and key != "id":
                project[key] = value
        project["updated_at"] = datetime.now().isoformat()

        try:
            self.conn.execute(
                """UPDATE projects SET name=:name, workspace=:workspace,
                   description=:description, status=:status, updated_at=:updated_at
                   WHERE id=:id""",
                project,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self._annotate_staleness(project)

    def archive_project(self, id: str) -> dict:
        """Set project status to inactive."""
        return self.update_project(id, status="inactive")

    def get_project(self, id: str) -> dict:
        """Get a single project by ID."""
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Project not found: {id}")
        return self._annotate_staleness(row_to_project(row))

    def list_projects(self, include_inactive: bool = False) -> List[dict]:
        """List all projects with staleness annotations."""
        if include_inactive:
            rows = self.conn.execute("SELECT * FROM projects").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM projects WHERE status = 'active'"
            ).fetchall()
        return [self._annotate_staleness(row_to_project(r)) for r in rows]

    def get_stale_projects(self) -> List[dict]:
        """Get active projects that are stale (updated_at > threshold)."""
        return [p for p in self.list_projects() if p["staleness"] == "stale"]

    # ================================================================
    # People CRUD
    # ================================================================

    def add_person(self, id: str, name: str, relationship: str) -> dict:
        """Add a new person."""
        person = person_to_row({
            "id": id, "name": name, "relationship": relationship,
        })
        try:
            self.conn.execute(
                """INSERT INTO people (id, name, relationship)
                   VALUES (:id, :name, :relationship)""",
                person,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return person

    def update_person(self, id: str, **updates) -> dict:
        """Update a person's details."""
        row = self.conn.execute(
            "SELECT * FROM people WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Person not found: {id}")

        person = row_to_person(row)
        for key, value in updates.items():
            if key in person and key != "id":
                person[key] = value

        try:
            self.conn.execute(
                """UPDATE people SET name=:name, relationship=:relationship
                   WHERE id=:id""",
                person,
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return person

    def remove_person(self, id: str) -> None:
        """Delete a person."""
        row = self.conn.execute(
            "SELECT * FROM people WHERE id = ?", (id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Person not found: {id}")
        self.conn.execute("DELETE FROM people WHERE id = ?", (id,))
        self.conn.commit()

    def list_people(self) -> List[dict]:
        """List all people."""
        rows = self.conn.execute("SELECT * FROM people").fetchall()
        return [row_to_person(r) for r in rows]

    # ================================================================
    # Context Queries (replaces ContextParser)
    # ================================================================

    def get_context(self) -> Dict:
        """
        Get full context for task categorization.

        Returns:
            {
                'projects': [...],  # with staleness annotations
                'people': [...]
            }
        """
        return {
            "projects": self.list_projects(),
            "people": self.list_people(),
        }

    def match_project(self, text: str) -> Tuple[Optional[str], float]:
        """
        Match text to a project with confidence score.
        Stale projects get reduced confidence. Inactive projects excluded.

        Returns:
            (project_id, confidence) or (None, 0.0)
        """
        projects = self.list_projects(include_inactive=False)
        text_lower = text.lower()

        best_match = None
        best_score = 0.0

        for project in projects:
            score = 0.0

            # Check for project name match
            if project["name"].lower() in text_lower:
                score += 0.5

            # Check for ID/slug match
            if project["id"].lower() in text_lower:
                score += 0.4

            # Check description words
            desc_words = set(project["description"].lower().split())
            text_words = set(text_lower.split())
            overlap = desc_words & text_words
            if overlap:
                score += min(0.3, len(overlap) * 0.1)

            # Apply staleness multiplier
            score *= project["confidence_multiplier"]

            if score > best_score:
                best_score = score
                best_match = project["id"]

        return best_match, min(1.0, best_score)

    def match_workspace(self, project_id: Optional[str],
                        text: str) -> Tuple[str, float]:
        """
        Infer workspace from matched project or text keywords.

        Returns:
            (workspace, confidence)
        """
        if project_id:
            try:
                project = self.get_project(project_id)
                confidence = project["confidence_multiplier"]
                return project["workspace"], confidence
            except ValueError:
                pass

        text_lower = text.lower()

        work_keywords = ['work', 'office', 'meeting', 'report',
                         'presentation', 'team']
        contract_keywords = ['client', 'contract', 'freelance', 'consulting']
        personal_keywords = ['personal', 'home', 'hobby', 'learning', 'study']

        work_score = sum(1 for kw in work_keywords if kw in text_lower)
        contract_score = sum(1 for kw in contract_keywords if kw in text_lower)
        personal_score = sum(1 for kw in personal_keywords if kw in text_lower)

        max_score = max(work_score, contract_score, personal_score)

        if max_score == 0:
            return 'personal', 0.3

        if work_score == max_score:
            return 'work', min(0.7, 0.4 + max_score * 0.1)
        elif contract_score == max_score:
            return 'contract', min(0.7, 0.4 + max_score * 0.1)
        else:
            return 'personal', min(0.7, 0.4 + max_score * 0.1)

    def detect_categories(self, text: str) -> Tuple[List[str], float]:
        """
        Detect task categories from text patterns.

        Returns:
            (categories, avg_confidence)
        """
        categories = []
        scores = []

        # People category patterns
        people_patterns = [
            r'\b(call|email|meet|contact|message|talk to|reach out to)\b',
            r'\b(with|about)\s+[A-Z][a-z]+',
        ]
        if any(re.search(p, text, re.IGNORECASE) for p in people_patterns):
            categories.append('people')
            scores.append(0.9)

        # Idea category patterns
        idea_patterns = [
            r'\b(idea|concept|thought|suggestion)\b',
            r'\b(we should|what if|maybe|consider)\b',
            r'\b(brainstorm|explore|research)\b',
        ]
        if any(re.search(p, text, re.IGNORECASE) for p in idea_patterns):
            categories.append('idea')
            scores.append(0.8)

        # Project category patterns
        project_patterns = [
            r'\b(implement|build|create|develop|fix|update|refactor)\b',
            r'\b(add|remove|change|modify|improve)\b',
            r'\b(deploy|release|launch|ship)\b',
        ]
        if any(re.search(p, text, re.IGNORECASE) for p in project_patterns):
            categories.append('project')
            scores.append(0.85)

        # Admin category patterns
        admin_patterns = [
            r'\b(remember|don\'t forget|make sure|remind)\b',
            r'\b(schedule|book|arrange|organize)\b',
            r'\b(submit|file|send|complete)\b',
        ]
        if any(re.search(p, text, re.IGNORECASE) for p in admin_patterns):
            categories.append('admin')
            scores.append(0.8)

        avg_confidence = sum(scores) / len(scores) if scores else 0.0

        if not categories:
            categories = ['admin']
            avg_confidence = 0.5

        return categories, avg_confidence

    # ================================================================
    # Internal
    # ================================================================

    def _annotate_staleness(self, project: dict) -> dict:
        """Add computed staleness and confidence_multiplier to a project dict."""
        if project["status"] == "inactive":
            project["staleness"] = "inactive"
            project["confidence_multiplier"] = 0.0
        else:
            updated = datetime.fromisoformat(project["updated_at"])
            age_days = (datetime.now() - updated).days
            if age_days > self.STALENESS_THRESHOLD_DAYS:
                project["staleness"] = "stale"
                project["confidence_multiplier"] = 0.4
            else:
                project["staleness"] = "fresh"
                project["confidence_multiplier"] = 0.9
        return project
