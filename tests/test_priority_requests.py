"""Tests for priority_requests feature."""

import pytest
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory
from src.learnbase.core.models import Note


def test_priority_requests_field_defaults():
    """Test that priority_requests field has empty list default."""
    note = Note(
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

    assert note.priority_requests == []


def test_priority_requests_serialization():
    """Test that priority_requests are properly serialized to markdown."""
    note = Note(
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
        priority_requests=[
            {
                "topic": "test topic",
                "reason": "test reason",
                "requested_at": "2026-01-22T10:00:00",
                "session_id": "session_123",
                "addressed_count": 0,
                "active": True
            }
        ]
    )

    markdown = note.to_markdown_file()

    # Check that priority_requests appears in the serialized output
    assert "priority_requests" in markdown
    assert "test topic" in markdown


def test_priority_requests_deserialization():
    """Test that priority_requests are properly deserialized from markdown."""
    with TemporaryDirectory() as tmpdir:
        # Create a test file with priority_requests
        test_file = Path(tmpdir) / "test.md"
        content = """---
title: Test Note
created: '2026-01-22T10:00:00'
review_mode: spaced
next_review: '2026-01-23T10:00:00'
interval_days: 1
ease_factor: 2.5
review_count: 0
priority_requests:
  - topic: test topic
    reason: test reason
    requested_at: '2026-01-22T10:00:00'
    session_id: session_123
    addressed_count: 0
    active: true
---

Test content
"""
        test_file.write_text(content)

        # Load the note
        note = Note.from_markdown_file(test_file)

        # Check that priority_requests was deserialized correctly
        assert len(note.priority_requests) == 1
        assert note.priority_requests[0]["topic"] == "test topic"
        assert note.priority_requests[0]["reason"] == "test reason"
        assert note.priority_requests[0]["addressed_count"] == 0
        assert note.priority_requests[0]["active"] is True


def test_priority_requests_roundtrip():
    """Test that priority_requests survive a serialize/deserialize cycle."""
    with TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"

        # Create a note with priority_requests
        note1 = Note(
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
            priority_requests=[
                {
                    "topic": "topic one",
                    "reason": "reason one",
                    "requested_at": "2026-01-22T10:00:00",
                    "session_id": "session_1",
                    "addressed_count": 0,
                    "active": True
                },
                {
                    "topic": "topic two",
                    "reason": "reason two",
                    "requested_at": "2026-01-22T11:00:00",
                    "session_id": "session_1",
                    "addressed_count": 1,
                    "active": False
                }
            ]
        )

        # Serialize to file
        test_file.write_text(note1.to_markdown_file())

        # Deserialize from file
        note2 = Note.from_markdown_file(test_file)

        # Check that priority_requests matches
        assert len(note2.priority_requests) == 2
        assert note2.priority_requests[0]["topic"] == "topic one"
        assert note2.priority_requests[0]["addressed_count"] == 0
        assert note2.priority_requests[0]["active"] is True
        assert note2.priority_requests[1]["topic"] == "topic two"
        assert note2.priority_requests[1]["addressed_count"] == 1
        assert note2.priority_requests[1]["active"] is False
