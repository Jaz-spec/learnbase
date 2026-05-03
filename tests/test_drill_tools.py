"""Tests for drill MCP tool handlers (happy-path + no-key degradation).

Uses skip_variants=True to avoid hitting the LLM in tests.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.learnbase.core.note_manager import NoteManager
from src.learnbase.core.models import DrillNote
from src.learnbase.core.spaced_rep import LADDER_INTERVALS
from src.learnbase.tools.drills import (
    handle_add_drill_card,
    handle_review_drill,
    handle_list_due_drills,
    handle_get_drill,
)


@pytest.fixture
def nm():
    with TemporaryDirectory() as tmpdir:
        yield NoteManager(notes_dir=Path(tmpdir))


def _text(resp):
    return resp[0].text


class TestAddDrillCard:
    def test_happy_path(self, nm):
        resp = handle_add_drill_card(nm, {
            "title": "Find Python TODOs",
            "prompt": "grep 'TODO' across all .py files recursively",
            "model_answer": "grep -rln 'TODO' --include='*.py' .",
            "language": "bash",
            "why_captured": "Got lost hunting for stale TODOs",
            "tags": ["grep", "search"],
            "skip_variants": True,
        })
        text = _text(resp)
        assert "Created drill card" in text
        # a single drill file was written
        drills = [n for n in nm.get_all_notes() if isinstance(n, DrillNote)]
        assert len(drills) == 1
        assert drills[0].title == "Find Python TODOs"
        assert drills[0].variants_status == "pending"  # skip_variants → pending
        assert drills[0].tags == ["grep", "search"]

    def test_missing_required_fields(self, nm):
        resp = handle_add_drill_card(nm, {"title": "x"})
        assert "Error" in _text(resp)

    def test_variants_failed_when_no_api_key(self, nm, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        resp = handle_add_drill_card(nm, {
            "title": "No key test",
            "prompt": "do a thing",
            "model_answer": "echo hi",
            "language": "bash",
            # skip_variants not set → will attempt generation and fail gracefully
        })
        text = _text(resp)
        assert "Created drill card" in text
        assert "failed" in text.lower() or "ANTHROPIC" in text
        drills = [n for n in nm.get_all_notes() if isinstance(n, DrillNote)]
        assert drills[0].variants_status == "failed"


class TestReviewDrill:
    def test_first_mode_pass_advances_ladder(self, nm):
        handle_add_drill_card(nm, {
            "title": "t", "prompt": "p", "model_answer": "a", "language": "bash",
            "skip_variants": True,
        })
        filename = next(n.filename for n in nm.get_all_notes() if isinstance(n, DrillNote))

        resp = handle_review_drill(nm, {"filename": filename, "passed": True})
        assert "PASS" in _text(resp)

        updated = nm.get_note(filename)
        assert isinstance(updated, DrillNote)
        assert updated.ladder_step == 1
        assert updated.review_count == 1
        assert updated.fail_streak == 0

    def test_free_practice_does_not_update_sr(self, nm):
        handle_add_drill_card(nm, {
            "title": "t", "prompt": "p", "model_answer": "a", "language": "bash",
            "skip_variants": True,
        })
        filename = next(n.filename for n in nm.get_all_notes() if isinstance(n, DrillNote))

        # First mode: pass → advances
        handle_review_drill(nm, {"filename": filename, "passed": True, "is_first_mode": True})
        first = nm.get_note(filename)
        assert first.ladder_step == 1
        first_next_review = first.next_review

        # Second mode on same card: fail → should NOT affect SR
        handle_review_drill(nm, {
            "filename": filename, "passed": False, "mode": "buddy", "is_first_mode": False
        })
        after = nm.get_note(filename)
        assert after.ladder_step == 1  # unchanged
        assert after.next_review == first_next_review  # unchanged
        assert after.review_count == 2  # count still increments

    def test_three_consecutive_fails_flag_rewrite(self, nm):
        handle_add_drill_card(nm, {
            "title": "t", "prompt": "p", "model_answer": "a", "language": "bash",
            "skip_variants": True,
        })
        filename = next(n.filename for n in nm.get_all_notes() if isinstance(n, DrillNote))

        for _ in range(3):
            handle_review_drill(nm, {"filename": filename, "passed": False})

        note = nm.get_note(filename)
        assert note.needs_rewrite is True

        # one pass clears the flag
        handle_review_drill(nm, {"filename": filename, "passed": True})
        note = nm.get_note(filename)
        assert note.needs_rewrite is False

    def test_invalid_mode_rejected(self, nm):
        handle_add_drill_card(nm, {
            "title": "t", "prompt": "p", "model_answer": "a", "language": "bash",
            "skip_variants": True,
        })
        filename = next(n.filename for n in nm.get_all_notes() if isinstance(n, DrillNote))

        resp = handle_review_drill(nm, {
            "filename": filename, "passed": True, "mode": "bogus"
        })
        assert "Error" in _text(resp)


class TestListAndGet:
    def test_list_due_empty(self, nm):
        resp = handle_list_due_drills(nm, {})
        assert "No drill cards currently due" in _text(resp)

    def test_list_due_returns_created_drill(self, nm):
        handle_add_drill_card(nm, {
            "title": "My drill", "prompt": "p", "model_answer": "a", "language": "python",
            "skip_variants": True,
        })
        resp = handle_list_due_drills(nm, {})
        text = _text(resp)
        assert "My drill" in text
        assert "python" in text

    def test_get_drill_returns_parsed_content(self, nm):
        handle_add_drill_card(nm, {
            "title": "Getter", "prompt": "find stuff", "model_answer": "grep foo",
            "language": "bash", "skip_variants": True, "why_captured": "needed it once",
        })
        filename = next(n.filename for n in nm.get_all_notes() if isinstance(n, DrillNote))
        resp = handle_get_drill(nm, {"filename": filename})
        text = _text(resp)
        assert "find stuff" in text
        assert "grep foo" in text
        assert "needed it once" in text

    def test_get_drill_rejects_non_drill(self, nm):
        # Create a review note then try to get_drill it.
        nm.create_note(title="regular", body="body", note_type="review")
        review_files = [n.filename for n in nm.get_all_notes() if not isinstance(n, DrillNote)]
        resp = handle_get_drill(nm, {"filename": review_files[0]})
        assert "not a drill" in _text(resp)
