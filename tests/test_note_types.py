"""Tests for creating both ReviewNote and ReferenceNote types."""

import pytest
from pathlib import Path
from datetime import datetime
from learnbase.core.note_manager import NoteManager
from learnbase.core.models import ReviewNote, ReferenceNote


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


class TestCreateReferenceNote:
    """Test creating reference notes."""

    def test_create_reference_note_explicit(self, nm):
        """Test creating a reference note with explicit note_type."""
        filename = nm.create_note(
            title="API Endpoints",
            body="GET /users - Returns all users",
            note_type="reference"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReferenceNote)
        assert note.title == "API Endpoints"
        assert note.body == "GET /users - Returns all users"
        assert note.filename == filename

    def test_reference_note_ignores_review_params(self, nm):
        """Test that review parameters are ignored for reference notes."""
        filename = nm.create_note(
            title="Test Reference",
            body="Content",
            note_type="reference",
            review_mode="spaced",  # Should be ignored
            schedule_pattern="1d,1w"  # Should be ignored
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReferenceNote)
        # Reference notes don't have review_mode or schedule_pattern
        assert not hasattr(note, 'review_mode')

    def test_reference_note_serialization(self, nm):
        """Test that reference notes serialize correctly."""
        filename = nm.create_note(
            title="Markdown Reference",
            body="# Header\n\nContent here",
            note_type="reference"
        )

        note = nm.get_note(filename)
        markdown = note.to_markdown_file()

        assert "type: reference" in markdown
        assert "title: Markdown Reference" in markdown
        assert "# Header" in markdown


class TestCreateReviewNote:
    """Test creating review notes."""

    def test_create_review_note_default(self, nm):
        """Test creating a review note with default parameters."""
        filename = nm.create_note(
            title="Python GIL",
            body="The Global Interpreter Lock..."
            # note_type defaults to 'review'
            # review_mode defaults to 'spaced'
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.review_mode == 'spaced'
        assert note.ease_factor == 2.5
        assert note.interval_days == 1

    def test_create_review_note_explicit(self, nm):
        """Test creating a review note with explicit note_type."""
        filename = nm.create_note(
            title="SQL Joins",
            body="INNER JOIN returns...",
            note_type="review",
            review_mode="spaced"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.review_mode == 'spaced'

    def test_create_review_note_scheduled(self, nm):
        """Test creating a review note with scheduled mode."""
        filename = nm.create_note(
            title="HTTP Methods",
            body="GET, POST, PUT, DELETE",
            note_type="review",
            review_mode="scheduled",
            schedule_pattern="1d,3d,1w,2w,1m"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.review_mode == 'scheduled'
        assert note.schedule_pattern == "1d,3d,1w,2w,1m"


class TestBackwardCompatibility:
    """Test that existing behavior is preserved."""

    def test_create_note_old_signature_positional(self, nm):
        """Test old signature with positional args still works."""
        filename = nm.create_note(
            "Test Note",
            "Test content"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.review_mode == 'spaced'

    def test_create_note_old_signature_with_review_mode(self, nm):
        """Test old signature with review_mode still works."""
        filename = nm.create_note(
            "Test Note",
            "Test content",
            review_mode="scheduled",
            schedule_pattern="1d,1w"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.review_mode == 'scheduled'

    def test_create_note_no_note_type_defaults_to_review(self, nm):
        """Test that omitting note_type creates a ReviewNote."""
        filename = nm.create_note(
            title="Default Type",
            body="Should be review note"
        )

        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)


class TestValidation:
    """Test validation of note creation parameters."""

    def test_invalid_note_type(self, nm):
        """Test that invalid note_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid note_type"):
            nm.create_note(
                title="Test",
                body="Content",
                note_type="invalid"
            )

    def test_scheduled_mode_without_pattern(self, nm):
        """Test that scheduled mode requires schedule_pattern."""
        with pytest.raises(ValueError, match="Schedule pattern required"):
            nm.create_note(
                title="Test",
                body="Content",
                note_type="review",
                review_mode="scheduled"
                # Missing schedule_pattern
            )

    def test_invalid_review_mode(self, nm):
        """Test that invalid review_mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid review_mode"):
            nm.create_note(
                title="Test",
                body="Content",
                note_type="review",
                review_mode="invalid"
            )


class TestNoteOperations:
    """Test that both note types work with existing operations."""

    def test_list_notes_includes_both_types(self, nm):
        """Test that list_notes shows both review and reference notes."""
        # Create one of each type
        nm.create_note("Review Note", "Review content", note_type="review")
        nm.create_note("Reference Note", "Reference content", note_type="reference")

        all_notes = nm.get_all_notes()
        assert len(all_notes) == 2

        review_notes = [n for n in all_notes if isinstance(n, ReviewNote)]
        reference_notes = [n for n in all_notes if isinstance(n, ReferenceNote)]

        assert len(review_notes) == 1
        assert len(reference_notes) == 1

    def test_get_stats_counts_both_types(self, nm):
        """Test that get_stats includes counts for both types."""
        # Create multiple notes of each type
        nm.create_note("Review 1", "Content 1", note_type="review")
        nm.create_note("Review 2", "Content 2", note_type="review")
        nm.create_note("Reference 1", "Content 1", note_type="reference")

        stats = nm.get_stats()
        assert stats["total_notes"] == 3
        assert stats["review_notes"] == 2
        assert stats["reference_notes"] == 1

    def test_edit_note_works_for_both_types(self, nm):
        """Test that editing works for both note types."""
        # Test editing review note
        review_filename = nm.create_note("Review", "Content", note_type="review")
        nm.update_note_content(review_filename, "Updated Review", "New content")
        review_note = nm.get_note(review_filename)
        assert review_note.title == "Updated Review"

        # Test editing reference note
        ref_filename = nm.create_note("Reference", "Content", note_type="reference")
        nm.update_note_content(ref_filename, "Updated Reference", "New content")
        ref_note = nm.get_note(ref_filename)
        assert ref_note.title == "Updated Reference"

    def test_delete_note_works_for_both_types(self, nm):
        """Test that deleting works for both note types."""
        # Test deleting review note
        review_filename = nm.create_note("Review", "Content", note_type="review")
        assert nm.delete_note(review_filename) is True
        assert nm.get_note(review_filename) is None

        # Test deleting reference note
        ref_filename = nm.create_note("Reference", "Content", note_type="reference")
        assert nm.delete_note(ref_filename) is True
        assert nm.get_note(ref_filename) is None

    def test_reference_note_cannot_be_reviewed(self, nm):
        """Test that reference notes cannot be reviewed."""
        filename = nm.create_note("Reference", "Content", note_type="reference")

        with pytest.raises(ValueError, match="reference note and cannot be reviewed"):
            nm.update_note_review(filename, rating=3)

    def test_get_due_notes_excludes_reference_notes(self, nm):
        """Test that get_due_notes only returns ReviewNotes."""
        nm.create_note("Review", "Content", note_type="review")
        nm.create_note("Reference", "Content", note_type="reference")

        due_notes = nm.get_due_notes()
        assert len(due_notes) == 1
        assert all(isinstance(n, ReviewNote) for n in due_notes)


class TestRoundtrip:
    """Test serialization and deserialization."""

    def test_reference_note_roundtrip(self, nm):
        """Test reference note can be saved and loaded."""
        filename = nm.create_note(
            title="API Reference",
            body="# Endpoints\n\n## GET /users",
            note_type="reference"
        )

        # Load from file
        note = nm.get_note(filename)
        assert isinstance(note, ReferenceNote)
        assert note.title == "API Reference"
        assert note.body == "# Endpoints\n\n## GET /users"

    def test_review_note_roundtrip(self, nm):
        """Test review note can be saved and loaded."""
        filename = nm.create_note(
            title="Python Concepts",
            body="GIL, decorators, generators",
            note_type="review",
            review_mode="spaced"
        )

        # Load from file
        note = nm.get_note(filename)
        assert isinstance(note, ReviewNote)
        assert note.title == "Python Concepts"
        assert note.review_mode == "spaced"
