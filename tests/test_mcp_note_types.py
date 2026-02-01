"""Integration tests for MCP tool interface with note types."""

import pytest
from learnbase.core.note_manager import NoteManager
from learnbase.tools.notes import handle_add_note


@pytest.fixture
def temp_notes_dir(tmp_path):
    """Provide a temporary notes directory."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    return notes_dir


@pytest.fixture
def nm(temp_notes_dir):
    """Provide a NoteManager instance."""
    return NoteManager(temp_notes_dir)


class TestMCPAddNoteToolInterface:
    """Test the MCP tool interface for adding notes."""

    def test_add_reference_note_via_tool(self, nm):
        """Test creating a reference note through the MCP tool."""
        arguments = {
            "title": "API Documentation",
            "body": "GET /api/v1/users - List all users",
            "note_type": "reference"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created reference note" in result[0].text
        assert "Type: Reference (storage only)" in result[0].text

    def test_add_review_note_default_via_tool(self, nm):
        """Test creating a review note with defaults through the MCP tool."""
        arguments = {
            "title": "Python Decorators",
            "body": "Functions that modify other functions"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created review note" in result[0].text
        assert "Mode: spaced" in result[0].text

    def test_add_review_note_explicit_via_tool(self, nm):
        """Test creating a review note with explicit type through the MCP tool."""
        arguments = {
            "title": "SQL Basics",
            "body": "SELECT * FROM users WHERE id = 1",
            "note_type": "review",
            "review_mode": "spaced"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created review note" in result[0].text
        assert "Mode: spaced" in result[0].text

    def test_add_review_note_scheduled_via_tool(self, nm):
        """Test creating a scheduled review note through the MCP tool."""
        arguments = {
            "title": "Git Commands",
            "body": "git commit, git push, git pull",
            "note_type": "review",
            "review_mode": "scheduled",
            "schedule_pattern": "1d,1w,1m"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created review note" in result[0].text

    def test_reference_note_ignores_review_params_via_tool(self, nm):
        """Test that review params are ignored for reference notes."""
        arguments = {
            "title": "Reference Doc",
            "body": "Some documentation",
            "note_type": "reference",
            "review_mode": "spaced",  # Should be ignored
            "schedule_pattern": "1d,1w"  # Should be ignored
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created reference note" in result[0].text
        # Verify it was actually created as reference
        all_notes = nm.get_all_notes()
        assert len(all_notes) == 1

    def test_backward_compatibility_no_note_type(self, nm):
        """Test that omitting note_type creates a review note."""
        arguments = {
            "title": "Test Note",
            "body": "Test content"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "✓ Created review note" in result[0].text

    def test_error_invalid_note_type_via_tool(self, nm):
        """Test that invalid note_type returns error."""
        arguments = {
            "title": "Test",
            "body": "Content",
            "note_type": "invalid"
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "Invalid note_type" in result[0].text

    def test_error_scheduled_without_pattern_via_tool(self, nm):
        """Test that scheduled mode without pattern returns error."""
        arguments = {
            "title": "Test",
            "body": "Content",
            "note_type": "review",
            "review_mode": "scheduled"
            # Missing schedule_pattern
        }

        result = handle_add_note(nm, arguments)

        assert len(result) == 1
        assert "Error:" in result[0].text
        assert "Schedule pattern required" in result[0].text
