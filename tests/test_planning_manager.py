"""Tests for PlanningManager (priorities and planning workflows)."""

import pytest
from datetime import datetime, timedelta
from tempfile import TemporaryDirectory
from pathlib import Path

from src.learnbase.core.context_manager import ContextManager
from src.learnbase.core.tasks_manager import TasksManager
from src.learnbase.core.planning_manager import PlanningManager
from src.learnbase.core.models import Task


@pytest.fixture
def managers():
    """Create all managers with a shared temp database."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        reviews_dir = Path(tmpdir) / "reviews"
        context_mgr = ContextManager(db_path=db_path)
        tasks_mgr = TasksManager(db_path=db_path)
        planning_mgr = PlanningManager(
            context_mgr, tasks_mgr, reviews_dir=reviews_dir
        )
        yield context_mgr, tasks_mgr, planning_mgr


@pytest.fixture
def populated(managers):
    """Managers with sample data."""
    context_mgr, tasks_mgr, planning_mgr = managers

    # Add projects
    context_mgr.add_project("learnbase", "LearnBase", "personal",
                            "MCP server for learning")
    context_mgr.add_project("distribution", "Distribution", "work",
                            "Email automation dashboard")

    # Add a task
    task = Task(
        id="2026-03-31-test-task",
        title="Test task",
        description="A test",
        categories=["project"],
        workspace="personal",
        project="learnbase",
        due=datetime.now() + timedelta(days=1),
        status="pending",
    )
    task.filename = Task.create_filename(task.id)
    tasks_mgr.create_task(task)

    return context_mgr, tasks_mgr, planning_mgr


# ================================================================
# Priority CRUD
# ================================================================

class TestPriorityCRUD:
    def test_create_priority(self, managers):
        _, _, planning = managers
        p = planning.create_priority(
            description="Ship calendar integration",
            scope="monthly",
            period="2026-04",
            project_id=None,
        )
        assert p["id"] == "monthly-2026-04-ship-calendar-integration"
        assert p["status"] == "pending"
        assert p["scope"] == "monthly"

    def test_create_priority_with_project(self, populated):
        _, _, planning = populated
        p = planning.create_priority(
            description="Add semantic search",
            scope="weekly",
            period="2026-W14",
            project_id="learnbase",
        )
        assert p["project_id"] == "learnbase"

    def test_get_priority(self, managers):
        _, _, planning = managers
        created = planning.create_priority("Test", "monthly", "2026-04")
        fetched = planning.get_priority(created["id"])
        assert fetched["description"] == "Test"

    def test_get_nonexistent_priority(self, managers):
        _, _, planning = managers
        with pytest.raises(ValueError, match="Priority not found"):
            planning.get_priority("nope")

    def test_update_priority_status(self, managers):
        _, _, planning = managers
        p = planning.create_priority("Test", "monthly", "2026-04")
        updated = planning.update_priority(p["id"], status="completed")
        assert updated["status"] == "completed"
        assert updated["completed_at"] is not None

    def test_update_priority_description(self, managers):
        _, _, planning = managers
        p = planning.create_priority("Old desc", "weekly", "2026-W14")
        updated = planning.update_priority(p["id"], description="New desc")
        assert updated["description"] == "New desc"

    def test_list_priorities_all(self, managers):
        _, _, planning = managers
        planning.create_priority("P1", "monthly", "2026-04")
        planning.create_priority("P2", "weekly", "2026-W14")
        all_p = planning.list_priorities()
        assert len(all_p) == 2

    def test_list_priorities_by_scope(self, managers):
        _, _, planning = managers
        planning.create_priority("Monthly", "monthly", "2026-04")
        planning.create_priority("Weekly", "weekly", "2026-W14")
        monthly = planning.list_priorities(scope="monthly")
        assert len(monthly) == 1
        assert monthly[0]["scope"] == "monthly"

    def test_list_priorities_by_period(self, managers):
        _, _, planning = managers
        planning.create_priority("April", "monthly", "2026-04")
        planning.create_priority("March", "monthly", "2026-03")
        april = planning.list_priorities(period="2026-04")
        assert len(april) == 1

    def test_list_priorities_by_status(self, managers):
        _, _, planning = managers
        p = planning.create_priority("Done", "monthly", "2026-04")
        planning.update_priority(p["id"], status="completed")
        planning.create_priority("Pending", "monthly", "2026-04")
        completed = planning.list_priorities(status="completed")
        assert len(completed) == 1

    def test_rolled_over_status(self, managers):
        _, _, planning = managers
        p = planning.create_priority("Rolled", "weekly", "2026-W13")
        updated = planning.update_priority(p["id"], status="rolled_over")
        assert updated["status"] == "rolled_over"


# ================================================================
# Planning Context
# ================================================================

class TestPlanningContext:
    def test_get_planning_context_monthly(self, populated):
        _, _, planning = populated
        planning.create_priority("Ship it", "monthly", datetime.now().strftime("%Y-%m"))

        ctx = planning.get_planning_context("monthly")
        assert "projects" in ctx
        assert "priorities" in ctx
        assert "tasks" in ctx
        assert "period" in ctx
        assert len(ctx["projects"]) == 2

    def test_get_planning_context_weekly(self, populated):
        _, _, planning = populated
        ctx = planning.get_planning_context("weekly")
        assert ctx["period"]["current_week"] is not None
        assert "gaps" in ctx

    def test_context_includes_tasks(self, populated):
        _, _, planning = populated
        ctx = planning.get_planning_context("weekly")
        assert len(ctx["tasks"]["pending"]) >= 1

    def test_stale_priorities_detected(self, managers):
        _, _, planning = managers
        # Create a priority for a past month
        planning.create_priority("Old goal", "monthly", "2026-01")
        ctx = planning.get_planning_context("monthly")
        assert len(ctx["stale_priorities"]) >= 1

    def test_gaps_detected_when_no_monthly(self, populated):
        _, _, planning = populated
        ctx = planning.get_planning_context("weekly")
        # No monthly priorities set, should flag gap
        assert "monthly" in ctx["gaps"]

    def test_task_summary_structure(self, populated):
        _, _, planning = populated
        ctx = planning.get_planning_context("weekly")
        task = ctx["tasks"]["pending"][0]
        assert "id" in task
        assert "title" in task
        assert "workspace" in task
        assert "priority_id" in task


# ================================================================
# Review Files
# ================================================================

class TestReviewFiles:
    def test_save_review_markdown(self, managers):
        _, _, planning = managers
        content = "# Monthly Review\n\nDecisions made..."
        path = planning.save_review_markdown("monthly", "2026-04", content)
        assert path.exists()
        assert path.read_text() == content

    def test_save_review_creates_directory(self, managers):
        _, _, planning = managers
        planning.save_review_markdown("weekly", "2026-W14", "content")
        assert planning.reviews_dir.exists()


# ================================================================
# Task Priority Link
# ================================================================

class TestTaskPriorityLink:
    def test_task_without_priority_loads(self, populated):
        _, tasks_mgr, _ = populated
        task = tasks_mgr.get_task("2026-03-31-test-task")
        assert task.priority_id is None

    def test_task_with_priority_id(self, populated):
        _, tasks_mgr, planning = populated
        priority = planning.create_priority("Goal", "weekly", "2026-W14")

        task = Task(
            id="2026-04-01-linked-task",
            title="Linked task",
            description="Has a priority",
            categories=["project"],
            workspace="personal",
            project=None,
            due=datetime.now() + timedelta(days=2),
            status="pending",
            priority_id=priority["id"],
        )
        task.filename = Task.create_filename(task.id)
        tasks_mgr.create_task(task)

        loaded = tasks_mgr.get_task("2026-04-01-linked-task")
        assert loaded.priority_id == priority["id"]


# ================================================================
# Slug Generation
# ================================================================

class TestSlugGeneration:
    def test_basic_slug(self, managers):
        _, _, planning = managers
        p = planning.create_priority("Ship feature X", "monthly", "2026-04")
        assert "ship-feature-x" in p["id"]

    def test_long_slug_truncated(self, managers):
        _, _, planning = managers
        long_desc = "This is a very long description that should be truncated to forty chars"
        p = planning.create_priority(long_desc, "monthly", "2026-04")
        # ID format: scope-period-slug
        slug_part = p["id"].split("-", 2)[-1]  # after "monthly-2026-04-"
        # The slug portion (after monthly-2026-04-) should be <= 40 chars
        # But the full slug is embedded in the ID
        assert len(p["id"]) <= len("monthly-2026-04-") + 40
