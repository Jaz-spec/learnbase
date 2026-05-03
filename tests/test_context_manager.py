"""Tests for ContextManager (SQLite-backed context for task categorization)."""

import pytest
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from pathlib import Path

from src.learnbase.core.context_manager import ContextManager


@pytest.fixture
def manager():
    """Create a ContextManager with a temp database."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield ContextManager(db_path=db_path)


@pytest.fixture
def populated_manager(manager):
    """ContextManager with sample data."""
    manager.add_project("learnbase", "LearnBase", "personal",
                        "MCP server for spaced repetition and task management")
    manager.add_project("distribution", "Distribution", "work",
                        "Full-stack dashboard for email automation and outreach")
    manager.add_person("dan", "Dan", "boss and CEO")
    manager.add_person("izaak", "Izaak", "CTO")
    return manager


# ================================================================
# Project CRUD
# ================================================================

class TestProjectCRUD:
    def test_add_project(self, manager):
        result = manager.add_project("test", "Test Project", "personal",
                                     "A test project")
        assert result["id"] == "test"
        assert result["name"] == "Test Project"
        assert result["workspace"] == "personal"
        assert result["staleness"] == "fresh"

    def test_add_duplicate_project_fails(self, manager):
        manager.add_project("test", "Test", "personal", "desc")
        with pytest.raises(Exception):
            manager.add_project("test", "Test2", "personal", "desc2")

    def test_get_project(self, populated_manager):
        project = populated_manager.get_project("learnbase")
        assert project["name"] == "LearnBase"
        assert project["workspace"] == "personal"

    def test_get_nonexistent_project(self, manager):
        with pytest.raises(ValueError, match="Project not found"):
            manager.get_project("nope")

    def test_update_project(self, populated_manager):
        result = populated_manager.update_project(
            "learnbase", description="Updated description"
        )
        assert result["description"] == "Updated description"
        assert result["staleness"] == "fresh"  # updated_at was just touched

    def test_update_touches_updated_at(self, populated_manager):
        before = populated_manager.get_project("learnbase")["updated_at"]
        populated_manager.update_project("learnbase", description="new")
        after = populated_manager.get_project("learnbase")["updated_at"]
        assert after >= before

    def test_archive_project(self, populated_manager):
        result = populated_manager.archive_project("learnbase")
        assert result["status"] == "inactive"
        assert result["staleness"] == "inactive"
        assert result["confidence_multiplier"] == 0.0

    def test_list_projects_excludes_inactive(self, populated_manager):
        populated_manager.archive_project("learnbase")
        projects = populated_manager.list_projects()
        assert len(projects) == 1
        assert projects[0]["id"] == "distribution"

    def test_list_projects_include_inactive(self, populated_manager):
        populated_manager.archive_project("learnbase")
        projects = populated_manager.list_projects(include_inactive=True)
        assert len(projects) == 2

    def test_invalid_workspace_rejected(self, manager):
        with pytest.raises(Exception):
            manager.add_project("bad", "Bad", "invalid_ws", "desc")


# ================================================================
# Staleness
# ================================================================

class TestStaleness:
    def test_fresh_project(self, manager):
        project = manager.add_project("fresh", "Fresh", "personal", "desc")
        assert project["staleness"] == "fresh"
        assert project["confidence_multiplier"] == 0.9

    def test_stale_project(self, manager):
        manager.add_project("old", "Old", "personal", "desc")
        # Manually backdate updated_at
        old_date = (datetime.now() - timedelta(days=15)).isoformat()
        manager.conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (old_date, "old")
        )
        manager.conn.commit()

        project = manager.get_project("old")
        assert project["staleness"] == "stale"
        assert project["confidence_multiplier"] == 0.4

    def test_exactly_14_days_is_not_stale(self, manager):
        manager.add_project("edge", "Edge", "personal", "desc")
        edge_date = (datetime.now() - timedelta(days=14)).isoformat()
        manager.conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (edge_date, "edge")
        )
        manager.conn.commit()

        project = manager.get_project("edge")
        assert project["staleness"] == "fresh"

    def test_15_days_is_stale(self, manager):
        manager.add_project("stale", "Stale", "personal", "desc")
        stale_date = (datetime.now() - timedelta(days=15)).isoformat()
        manager.conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (stale_date, "stale")
        )
        manager.conn.commit()

        project = manager.get_project("stale")
        assert project["staleness"] == "stale"

    def test_get_stale_projects(self, populated_manager):
        old_date = (datetime.now() - timedelta(days=20)).isoformat()
        populated_manager.conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (old_date, "distribution")
        )
        populated_manager.conn.commit()

        stale = populated_manager.get_stale_projects()
        assert len(stale) == 1
        assert stale[0]["id"] == "distribution"

    def test_inactive_not_in_stale(self, populated_manager):
        populated_manager.archive_project("learnbase")
        stale = populated_manager.get_stale_projects()
        assert all(p["id"] != "learnbase" for p in stale)


# ================================================================
# People CRUD
# ================================================================

class TestPeopleCRUD:
    def test_add_person(self, manager):
        person = manager.add_person("dan", "Dan", "boss and CEO")
        assert person["id"] == "dan"
        assert person["relationship"] == "boss and CEO"

    def test_update_person(self, populated_manager):
        result = populated_manager.update_person(
            "dan", relationship="CEO and founder"
        )
        assert result["relationship"] == "CEO and founder"

    def test_remove_person(self, populated_manager):
        populated_manager.remove_person("dan")
        people = populated_manager.list_people()
        assert len(people) == 1
        assert people[0]["id"] == "izaak"

    def test_remove_nonexistent_person(self, manager):
        with pytest.raises(ValueError, match="Person not found"):
            manager.remove_person("nobody")

    def test_list_people(self, populated_manager):
        people = populated_manager.list_people()
        assert len(people) == 2
        names = {p["name"] for p in people}
        assert names == {"Dan", "Izaak"}


# ================================================================
# Context Queries
# ================================================================

class TestContextQueries:
    def test_get_context(self, populated_manager):
        ctx = populated_manager.get_context()
        assert len(ctx["projects"]) == 2
        assert len(ctx["people"]) == 2

    def test_get_context_empty_db(self, manager):
        ctx = manager.get_context()
        assert ctx["projects"] == []
        assert ctx["people"] == []

    def test_match_project_by_name(self, populated_manager):
        project_id, confidence = populated_manager.match_project(
            "working on LearnBase today"
        )
        assert project_id == "learnbase"
        assert confidence > 0.0

    def test_match_project_by_description(self, populated_manager):
        project_id, confidence = populated_manager.match_project(
            "email automation dashboard"
        )
        assert project_id == "distribution"
        assert confidence > 0.0

    def test_match_project_stale_lower_confidence(self, populated_manager):
        # Get fresh confidence
        _, fresh_conf = populated_manager.match_project("LearnBase")

        # Make it stale
        old_date = (datetime.now() - timedelta(days=20)).isoformat()
        populated_manager.conn.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (old_date, "learnbase")
        )
        populated_manager.conn.commit()

        _, stale_conf = populated_manager.match_project("LearnBase")
        assert stale_conf < fresh_conf

    def test_match_project_inactive_excluded(self, populated_manager):
        populated_manager.archive_project("learnbase")
        project_id, confidence = populated_manager.match_project("LearnBase")
        # Should not match the inactive project
        assert project_id != "learnbase"

    def test_match_project_no_match(self, populated_manager):
        project_id, confidence = populated_manager.match_project(
            "completely unrelated text"
        )
        assert project_id is None
        assert confidence == 0.0

    def test_match_workspace_from_project(self, populated_manager):
        workspace, confidence = populated_manager.match_workspace(
            "distribution", "anything"
        )
        assert workspace == "work"
        assert confidence == 0.9  # fresh project

    def test_match_workspace_keyword_fallback(self, populated_manager):
        workspace, confidence = populated_manager.match_workspace(
            None, "schedule a meeting at the office"
        )
        assert workspace == "work"

    def test_match_workspace_default(self, populated_manager):
        workspace, confidence = populated_manager.match_workspace(
            None, "random stuff"
        )
        assert workspace == "personal"
        assert confidence == 0.3


# ================================================================
# Category Detection
# ================================================================

class TestCategoryDetection:
    def test_people_category(self, manager):
        cats, conf = manager.detect_categories("call Dan about the project")
        assert "people" in cats

    def test_idea_category(self, manager):
        cats, conf = manager.detect_categories("what if we brainstorm ideas")
        assert "idea" in cats

    def test_project_category(self, manager):
        cats, conf = manager.detect_categories("implement the new API endpoint")
        assert "project" in cats

    def test_admin_category(self, manager):
        cats, conf = manager.detect_categories("remember to submit the form")
        assert "admin" in cats

    def test_multiple_categories(self, manager):
        cats, conf = manager.detect_categories(
            "call Dan to brainstorm ideas about the build"
        )
        assert len(cats) >= 2

    def test_default_admin(self, manager):
        cats, conf = manager.detect_categories("xyz")
        assert cats == ["admin"]
        assert conf == 0.5
