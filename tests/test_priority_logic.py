"""Tests for priority request logic in NoteManager."""

import pytest
from pathlib import Path
from datetime import datetime
from tempfile import TemporaryDirectory
from src.learnbase.core.note_manager import NoteManager
from src.learnbase.core.models import Note


@pytest.fixture
def temp_note_manager():
    """Create a temporary NoteManager for testing."""
    with TemporaryDirectory() as tmpdir:
        manager = NoteManager(notes_dir=Path(tmpdir))
        yield manager


@pytest.fixture
def sample_note(temp_note_manager):
    """Create a sample note for testing."""
    temp_note_manager.create_note(
        title="Test Note",
        body="Test content",
        review_mode="spaced"
    )
    return "test-note.md"


def test_add_new_priority_request(temp_note_manager, sample_note):
    """Test adding a new priority request."""
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "test topic", "reason": "test reason"}],
        addressed_topics=[],
        session_id="session_1"
    )

    note = temp_note_manager.get_note(sample_note)
    assert len(note.priority_requests) == 1
    assert note.priority_requests[0]["topic"] == "test topic"
    assert note.priority_requests[0]["reason"] == "test reason"
    assert note.priority_requests[0]["addressed_count"] == 0
    assert note.priority_requests[0]["active"] is True


def test_update_existing_priority_request(temp_note_manager, sample_note):
    """Test updating an existing priority request."""
    # Add initial request
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "test topic", "reason": "initial reason"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Update with same topic (case-insensitive)
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "Test Topic", "reason": "updated reason"}],
        addressed_topics=[],
        session_id="session_2"
    )

    note = temp_note_manager.get_note(sample_note)
    assert len(note.priority_requests) == 1  # Should not create duplicate
    assert note.priority_requests[0]["reason"] == "updated reason"


def test_address_priority_once(temp_note_manager, sample_note):
    """Test addressing a priority once increments count."""
    # Add priority
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "test topic", "reason": "test"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Address it once
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["test topic"],
        session_id="session_2"
    )

    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests[0]["addressed_count"] == 1
    assert note.priority_requests[0]["active"] is True  # Still active


def test_address_priority_twice_deactivates(temp_note_manager, sample_note):
    """Test addressing a priority twice deactivates it."""
    # Add priority
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "test topic", "reason": "test"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Address it first time
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["test topic"],
        session_id="session_2"
    )

    # Address it second time
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["test topic"],
        session_id="session_3"
    )

    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests[0]["addressed_count"] == 2
    assert note.priority_requests[0]["active"] is False  # Deactivated


def test_address_multiple_priorities(temp_note_manager, sample_note):
    """Test addressing multiple priorities in one session."""
    # Add multiple priorities
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[
            {"topic": "topic one", "reason": "reason one"},
            {"topic": "topic two", "reason": "reason two"}
        ],
        addressed_topics=[],
        session_id="session_1"
    )

    # Address both
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["topic one", "topic two"],
        session_id="session_2"
    )

    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests[0]["addressed_count"] == 1
    assert note.priority_requests[1]["addressed_count"] == 1


def test_add_and_address_in_same_session(temp_note_manager, sample_note):
    """Test adding a new priority and addressing an existing one in the same session."""
    # Add initial priority
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "existing topic", "reason": "test"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Add new priority AND address existing one
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "new topic", "reason": "new reason"}],
        addressed_topics=["existing topic"],
        session_id="session_2"
    )

    note = temp_note_manager.get_note(sample_note)
    assert len(note.priority_requests) == 2
    assert note.priority_requests[0]["topic"] == "existing topic"
    assert note.priority_requests[0]["addressed_count"] == 1
    assert note.priority_requests[1]["topic"] == "new topic"
    assert note.priority_requests[1]["addressed_count"] == 0


def test_case_insensitive_matching(temp_note_manager, sample_note):
    """Test that topic matching is case-insensitive."""
    # Add priority
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "Test Topic", "reason": "test"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Address with different case
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["test topic"],
        session_id="session_2"
    )

    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests[0]["addressed_count"] == 1


def test_empty_requests_and_topics(temp_note_manager, sample_note):
    """Test that empty requests and topics are handled gracefully."""
    # Should not raise error
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=[],
        session_id="session_1"
    )

    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests == []


def test_addressing_nonexistent_topic(temp_note_manager, sample_note):
    """Test addressing a topic that doesn't exist (should be ignored)."""
    # Add one priority
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[{"topic": "real topic", "reason": "test"}],
        addressed_topics=[],
        session_id="session_1"
    )

    # Try to address a different topic
    temp_note_manager.update_priority_requests(
        filename=sample_note,
        new_requests=[],
        addressed_topics=["nonexistent topic"],
        session_id="session_2"
    )

    # Real topic should not be affected
    note = temp_note_manager.get_note(sample_note)
    assert note.priority_requests[0]["addressed_count"] == 0
