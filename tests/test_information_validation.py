"""Tests for information validation feature."""

import pytest
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory
from src.learnbase.core.models import Note, ReviewNote
from src.learnbase.core.note_manager import NoteManager


# ============================================================================
# Data Model Tests
# ============================================================================

def test_confidence_score_field_defaults():
    """Test that confidence_score field defaults to None."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0
    )

    assert note.confidence_score is None


def test_sources_field_defaults():
    """Test that sources field defaults to empty list."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0
    )

    assert note.sources == []


def test_set_confidence_score_valid():
    """Test setting valid confidence scores."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0
    )

    # Test valid scores
    note.set_confidence_score(0.0)
    assert note.confidence_score == 0.0

    note.set_confidence_score(0.5)
    assert note.confidence_score == 0.5

    note.set_confidence_score(1.0)
    assert note.confidence_score == 1.0


def test_set_confidence_score_invalid_range():
    """Test that invalid confidence scores raise ValueError."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0
    )

    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        note.set_confidence_score(-0.1)

    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        note.set_confidence_score(1.1)


def test_set_confidence_score_invalid_type():
    """Test that non-numeric confidence scores raise ValueError."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0
    )

    with pytest.raises(ValueError, match="must be numeric"):
        note.set_confidence_score("0.5")


def test_confidence_score_serialization():
    """Test that confidence_score is properly serialized to markdown."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0,
        confidence_score=0.75
    )

    markdown = note.to_markdown_file()
    assert "confidence_score" in markdown
    assert "0.75" in markdown


def test_sources_serialization():
    """Test that sources are properly serialized to markdown."""
    note = ReviewNote(
        filename="test.md",
        title="Test Note",
        body="Test content",
        review_mode="spaced",
        schedule_pattern=None,
        created_at=datetime.now(),
        last_reviewed=None,
        next_review=datetime.now(),
        interval_days=1,
        ease_factor=2.5,
        review_count=0,
        sources=[
            {
                "url": "https://example.com",
                "title": "Example Source",
                "accessed_date": "2026-01-23",
                "note": "Test note"
            }
        ]
    )

    markdown = note.to_markdown_file()
    assert "sources" in markdown
    assert "https://example.com" in markdown


def test_confidence_score_deserialization():
    """Test that confidence_score is properly deserialized from markdown."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        content = """---
title: Test Note
created: '2026-01-22T10:00:00'
review_mode: spaced
next_review: '2026-01-23T10:00:00'
interval_days: 1
ease_factor: 2.5
review_count: 0
confidence_score: 0.75
---

Test content
"""
        test_file.write_text(content)

        note = Note.from_markdown_file(test_file)
        assert note.confidence_score == 0.75


def test_sources_deserialization():
    """Test that sources are properly deserialized from markdown."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        content = """---
title: Test Note
created: '2026-01-22T10:00:00'
review_mode: spaced
next_review: '2026-01-23T10:00:00'
interval_days: 1
ease_factor: 2.5
review_count: 0
sources:
  - url: https://example.com
    title: Example Source
    accessed_date: '2026-01-23'
    note: Test note
---

Test content
"""
        test_file.write_text(content)

        note = Note.from_markdown_file(test_file)
        assert len(note.sources) == 1
        assert note.sources[0]["url"] == "https://example.com"
        assert note.sources[0]["title"] == "Example Source"


def test_backward_compatibility():
    """Test that notes without confidence/sources load correctly."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        content = """---
title: Test Note
created: '2026-01-22T10:00:00'
review_mode: spaced
next_review: '2026-01-23T10:00:00'
interval_days: 1
ease_factor: 2.5
review_count: 0
---

Test content
"""
        test_file.write_text(content)

        note = Note.from_markdown_file(test_file)
        assert note.confidence_score is None
        assert note.sources == []


def test_roundtrip_with_confidence_and_sources():
    """Test that confidence and sources survive a serialize/deserialize cycle."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"

        note1 = ReviewNote(
            filename="test.md",
            title="Test Note",
            body="Test content",
            review_mode="spaced",
            schedule_pattern=None,
            created_at=datetime.now(),
            last_reviewed=None,
            next_review=datetime.now(),
            interval_days=1,
            ease_factor=2.5,
            review_count=0,
            confidence_score=0.85,
            sources=[
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "accessed_date": "2026-01-23"
                },
                {
                    "url": "https://example2.com",
                    "title": "Example 2"
                }
            ]
        )

        # Serialize to file
        test_file.write_text(note1.to_markdown_file())

        # Deserialize from file
        note2 = Note.from_markdown_file(test_file)

        # Check values match
        assert note2.confidence_score == 0.85
        assert len(note2.sources) == 2
        assert note2.sources[0]["url"] == "https://example.com"
        assert note2.sources[1]["url"] == "https://example2.com"


# ============================================================================
# Filtering Logic Tests
# ============================================================================

def test_get_notes_needing_verification():
    """Test filtering notes that need verification (no sources)."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create notes with and without sources
        nm.create_note("Verified Note", "Has sources")
        verified = nm.get_note("verified-note.md")
        verified.sources = [{"url": "https://example.com"}]
        nm._save_note(verified, Path(tmpdir) / "verified-note.md")

        nm.create_note("Unverified Note", "No sources")

        # Test filtering
        unverified = nm.get_notes_needing_verification()
        assert len(unverified) == 1
        assert unverified[0].filename == "unverified-note.md"


def test_get_notes_needing_verification_with_limit():
    """Test get_notes_needing_verification with limit."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create multiple unverified notes
        nm.create_note("Unverified 1", "No sources 1")
        nm.create_note("Unverified 2", "No sources 2")
        nm.create_note("Unverified 3", "No sources 3")

        # Test limit
        unverified = nm.get_notes_needing_verification(limit=2)
        assert len(unverified) == 2


def test_get_notes_with_low_confidence():
    """Test filtering notes with low confidence."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create notes with various confidence scores
        nm.create_note("High Confidence", "0.9 confidence")
        high = nm.get_note("high-confidence.md")
        high.confidence_score = 0.9
        nm._save_note(high, Path(tmpdir) / "high-confidence.md")

        nm.create_note("Low Confidence", "0.4 confidence")
        low = nm.get_note("low-confidence.md")
        low.confidence_score = 0.4
        nm._save_note(low, Path(tmpdir) / "low-confidence.md")

        nm.create_note("No Confidence", "None confidence")

        # Test filtering (default threshold 0.6)
        low_conf = nm.get_notes_with_low_confidence()
        assert len(low_conf) == 1
        assert low_conf[0].filename == "low-confidence.md"


def test_get_notes_with_low_confidence_custom_threshold():
    """Test get_notes_with_low_confidence with custom threshold."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create notes with various confidence scores
        nm.create_note("Med Confidence", "0.7 confidence")
        med = nm.get_note("med-confidence.md")
        med.confidence_score = 0.7
        nm._save_note(med, Path(tmpdir) / "med-confidence.md")

        nm.create_note("Low Confidence", "0.4 confidence")
        low = nm.get_note("low-confidence.md")
        low.confidence_score = 0.4
        nm._save_note(low, Path(tmpdir) / "low-confidence.md")

        # Test with threshold 0.8
        low_conf = nm.get_notes_with_low_confidence(threshold=0.8)
        assert len(low_conf) == 2


def test_get_notes_with_low_confidence_sorted():
    """Test that low confidence notes are sorted lowest first."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create notes with various confidence scores
        nm.create_note("Note 1", "0.5 confidence")
        n1 = nm.get_note("note-1.md")
        n1.confidence_score = 0.5
        nm._save_note(n1, Path(tmpdir) / "note-1.md")

        nm.create_note("Note 2", "0.2 confidence")
        n2 = nm.get_note("note-2.md")
        n2.confidence_score = 0.2
        nm._save_note(n2, Path(tmpdir) / "note-2.md")

        nm.create_note("Note 3", "0.4 confidence")
        n3 = nm.get_note("note-3.md")
        n3.confidence_score = 0.4
        nm._save_note(n3, Path(tmpdir) / "note-3.md")

        # Test sorting
        low_conf = nm.get_notes_with_low_confidence()
        assert len(low_conf) == 3
        assert low_conf[0].confidence_score == 0.2
        assert low_conf[1].confidence_score == 0.4
        assert low_conf[2].confidence_score == 0.5


def test_get_notes_with_low_confidence_invalid_threshold():
    """Test that invalid thresholds raise ValueError."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            nm.get_notes_with_low_confidence(threshold=-0.1)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            nm.get_notes_with_low_confidence(threshold=1.5)

        with pytest.raises(ValueError, match="must be numeric"):
            nm.get_notes_with_low_confidence(threshold="0.5")


def test_get_due_notes_require_verified():
    """Test get_due_notes with require_verified filter."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create a verified note (due today)
        nm.create_note("Verified Note", "Has sources")
        verified = nm.get_note("verified-note.md")
        verified.sources = [{"url": "https://example.com"}]
        verified.confidence_score = 0.8
        nm._save_note(verified, Path(tmpdir) / "verified-note.md")

        # Create an unverified note (due today)
        nm.create_note("Unverified Note", "No sources")

        # Create a low confidence note (due today)
        nm.create_note("Low Confidence Note", "Low confidence")
        low = nm.get_note("low-confidence-note.md")
        low.sources = [{"url": "https://example.com"}]
        low.confidence_score = 0.4
        nm._save_note(low, Path(tmpdir) / "low-confidence-note.md")

        # Test without filter (all notes)
        all_due = nm.get_due_notes()
        assert len(all_due) == 3

        # Test with require_verified (should exclude unverified and low confidence)
        verified_due = nm.get_due_notes(require_verified=True)
        assert len(verified_due) == 1
        assert verified_due[0].filename == "verified-note.md"


def test_get_due_notes_require_verified_with_none_confidence():
    """Test that notes with None confidence and sources are included when verified required."""
    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create a note with sources but no confidence score
        nm.create_note("Note With Sources", "Has sources, no confidence")
        note = nm.get_note("note-with-sources.md")
        note.sources = [{"url": "https://example.com"}]
        # confidence_score remains None
        nm._save_note(note, Path(tmpdir) / "note-with-sources.md")

        # Test with require_verified (should include note with sources and None confidence)
        verified_due = nm.get_due_notes(require_verified=True)
        assert len(verified_due) == 1
        assert verified_due[0].filename == "note-with-sources.md"


# ============================================================================
# Tool Integration Tests
# ============================================================================

def test_list_notes_with_verification_indicators(capsys):
    """Test that list_notes includes verification indicators."""
    from src.learnbase.tools.notes import handle_list_notes

    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create notes with different verification statuses
        nm.create_note("Verified Note", "Has sources")
        verified = nm.get_note("verified-note.md")
        verified.sources = [{"url": "https://example.com"}]
        verified.confidence_score = 0.8
        nm._save_note(verified, Path(tmpdir) / "verified-note.md")

        nm.create_note("Unverified Note", "No sources")

        # Call handler
        result = handle_list_notes(nm, {})
        text = result[0].text

        # Check for indicators
        assert "verified" in text.lower()
        assert "unverified" in text.lower() or "⚠️" in text


def test_list_notes_needs_verification_filter():
    """Test list_notes with needs_verification filter."""
    from src.learnbase.tools.notes import handle_list_notes

    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create mixed notes
        nm.create_note("Verified Note", "Has sources")
        verified = nm.get_note("verified-note.md")
        verified.sources = [{"url": "https://example.com"}]
        nm._save_note(verified, Path(tmpdir) / "verified-note.md")

        nm.create_note("Unverified Note", "No sources")

        # Call handler with filter
        result = handle_list_notes(nm, {"needs_verification": True})
        text = result[0].text

        # Should only show unverified note
        assert "unverified-note.md" in text.lower()
        # Check that verified-note.md does not appear in the file listing
        # (it might appear in the header text "needs verification")
        assert "file**: verified-note.md" not in text.lower()


def test_get_due_notes_with_indicators():
    """Test that get_due_notes includes verification indicators."""
    from src.learnbase.tools.review import handle_get_due_notes

    with TemporaryDirectory() as tmpdir:
        nm = NoteManager(tmpdir)

        # Create unverified note (due today)
        nm.create_note("Unverified Note", "No sources")

        # Call handler
        result = handle_get_due_notes(nm, {})
        text = result[0].text

        # Check for indicators (verification status is shown)
        assert "Un-verified" in text or "Unverified" in text
