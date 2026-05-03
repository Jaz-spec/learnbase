"""Tests for DrillNote model: body round-trip and file round-trip."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.learnbase.core.models import Note, DrillNote, ReviewNote


class TestBodyRoundTrip:
    def test_build_and_parse_single_line(self):
        body = DrillNote.build_body(
            prompt="Show human-readable disk usage excluding tmpfs",
            model_answer="df -h | grep -v tmpfs",
            language="bash",
        )
        prompt, answer = DrillNote.parse_body(body)
        assert prompt == "Show human-readable disk usage excluding tmpfs"
        assert answer == "df -h | grep -v tmpfs"

    def test_build_and_parse_multi_line(self):
        body = DrillNote.build_body(
            prompt="List the top 5 largest files under /var/log",
            model_answer="find /var/log -type f -exec du -h {} + \\\n  | sort -rh \\\n  | head -5",
            language="bash",
        )
        prompt, answer = DrillNote.parse_body(body)
        assert "top 5 largest" in prompt
        assert "find /var/log" in answer
        assert "head -5" in answer
        assert answer.count("\n") >= 2

    def test_parse_missing_sections_returns_empty(self):
        prompt, answer = DrillNote.parse_body("just a body with no headers")
        assert prompt == ""
        assert answer == ""

    def test_language_preserved_in_fence(self):
        body = DrillNote.build_body("desc", "print('hi')", "python")
        assert "```python" in body
        prompt, answer = DrillNote.parse_body(body)
        assert answer == "print('hi')"


class TestFileRoundTrip:
    def test_write_and_read_back(self):
        with TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "drill-test.md"
            body = DrillNote.build_body(
                "find .py files containing 'TODO'",
                "grep -rln 'TODO' --include='*.py' .",
                "bash",
            )
            drill = DrillNote(
                filename="drill-test.md",
                title="Find Python TODOs",
                body=body,
                language="bash",
                tags=["grep", "search"],
                why_captured="Got lost hunting for stale TODOs in a big repo.",
                sources=[],
                created_at=datetime(2026, 4, 24, 10, 0, 0),
                last_reviewed=None,
                next_review=datetime(2026, 4, 25),
                ladder_step=0,
                review_count=0,
                fail_streak=0,
                needs_rewrite=False,
                variants_status="pending",
                buddy_variants=[],
                reverse_variants=[],
            )
            filepath.write_text(drill.to_markdown_file())

            loaded = Note.from_markdown_file(filepath)
            assert isinstance(loaded, DrillNote)
            assert loaded.title == "Find Python TODOs"
            assert loaded.language == "bash"
            assert loaded.tags == ["grep", "search"]
            assert loaded.ladder_step == 0
            assert loaded.variants_status == "pending"
            p, a = loaded.parse_prompt_and_answer()
            assert "TODO" in p
            assert "grep -rln" in a

    def test_variants_round_trip(self):
        with TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "drill-v.md"
            buddy = [
                {"broken": "df -h", "bug": "missing tmpfs filter"},
                {"broken": "df | grep -v tmpfs", "bug": "missing -h flag"},
            ]
            reverse = [
                {"code": "df -h | grep -v tmpfs", "correct": True},
                {"code": "df -H | grep tmpfs", "correct": False, "issue": "wrong filter direction"},
            ]
            drill = DrillNote(
                filename="drill-v.md",
                title="Disk usage",
                body=DrillNote.build_body("q", "a", "bash"),
                language="bash",
                tags=[],
                why_captured="",
                sources=[],
                created_at=datetime.now(),
                last_reviewed=None,
                next_review=datetime.now(),
                ladder_step=0,
                review_count=0,
                fail_streak=0,
                needs_rewrite=False,
                variants_status="ready",
                buddy_variants=buddy,
                reverse_variants=reverse,
            )
            filepath.write_text(drill.to_markdown_file())

            loaded = Note.from_markdown_file(filepath)
            assert isinstance(loaded, DrillNote)
            assert loaded.variants_status == "ready"
            assert loaded.buddy_variants == buddy
            assert loaded.reverse_variants == reverse

    def test_dispatcher_still_returns_review_note_for_review_type(self):
        """Regression: adding the drill branch must not break existing dispatch."""
        with TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "rn.md"
            rn = ReviewNote(
                filename="rn.md",
                title="Existing review note",
                body="some body",
                review_mode="spaced",
                schedule_pattern=None,
                created_at=datetime.now(),
                last_reviewed=None,
                next_review=datetime.now(),
                interval_days=1,
                ease_factor=2.5,
                review_count=0,
            )
            filepath.write_text(rn.to_markdown_file())
            loaded = Note.from_markdown_file(filepath)
            assert isinstance(loaded, ReviewNote)
