#!/usr/bin/env python3
"""Capture a drill card from the shell with EDITOR-driven prompts.

Used by the zsh widget (scripts/zsh_drill_widget.zsh) which binds Ctrl+X Ctrl+D
to capture the current command line as a drill card.

Usage:
    capture_drill.py [--language LANG] [--prefill-answer "<command>"]

The script opens $EDITOR with a template, parses the result, and calls
NoteManager.create_drill_note(...) directly. AI variant generation runs
synchronously if ANTHROPIC_API_KEY is set; otherwise the card is saved
with variants_status='failed' and the user can regenerate later.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


TEMPLATE = """# Drill capture — fill the fields below the [TAGS] markers, save, and exit.
# Lines starting with '#' are comments and stripped on save.
# Required: TITLE, PROMPT, ANSWER, LANGUAGE.

[TITLE]


[LANGUAGE]
{language}

[PROMPT]


[ANSWER]
{prefill}

[WHY]


[TAGS]

"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a drill card from the shell.")
    parser.add_argument("--language", default="bash", help="Code language tag (default: bash)")
    parser.add_argument("--prefill-answer", default="", help="Pre-fill the [ANSWER] field")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from learnbase.core.note_manager import NoteManager
        from learnbase.core.rag_manager import RAGManager
        from learnbase.core.llm_generator import generate_variants, LLMUnavailableError
    except Exception as e:
        print(f"capture_drill: import failed: {e}", file=sys.stderr)
        return 1

    template = TEMPLATE.format(language=args.language, prefill=args.prefill_answer)

    raw = open_in_editor(template)
    if raw is None:
        print("capture_drill: editor exited without saving", file=sys.stderr)
        return 1

    sections = parse_template(raw)
    missing = [k for k in ("TITLE", "LANGUAGE", "PROMPT", "ANSWER") if not sections.get(k)]
    if missing:
        print(f"capture_drill: missing required fields: {', '.join(missing)}", file=sys.stderr)
        return 2

    nm = NoteManager()
    try:
        rag = RAGManager(note_manager=nm)
        nm.rag_manager = rag
    except Exception:
        pass

    if not getattr(parser, "_force", False):
        similar = nm.find_similar_drills(prompt=sections["PROMPT"], threshold=0.75, limit=3)
        if similar:
            print("capture_drill: similar drills already exist:", file=sys.stderr)
            for m in similar:
                print(f"  - {m.get('filename')}: {m.get('title')}  (sim={m.get('similarity'):.2f})", file=sys.stderr)
            print("  re-run with --force to create anyway, or edit the existing card.", file=sys.stderr)
            return 3

    buddy, reverse, status = [], [], "pending"
    try:
        result = generate_variants(
            prompt=sections["PROMPT"],
            model_answer=sections["ANSWER"],
            language=sections["LANGUAGE"],
        )
        buddy = result["buddy"]
        reverse = result["reverse"]
        status = "ready"
    except LLMUnavailableError as e:
        status = "failed"
        print(f"capture_drill: variants skipped ({e}); card will save without them.", file=sys.stderr)
    except Exception as e:
        status = "failed"
        print(f"capture_drill: variants failed ({e}); card will save without them.", file=sys.stderr)

    tags = []
    if sections.get("TAGS"):
        for t in sections["TAGS"].split(","):
            t = t.strip()
            if t:
                tags.append(t)

    filename = nm.create_drill_note(
        title=sections["TITLE"],
        prompt=sections["PROMPT"],
        model_answer=sections["ANSWER"],
        language=sections["LANGUAGE"],
        why_captured=sections.get("WHY", ""),
        tags=tags,
        buddy_variants=buddy,
        reverse_variants=reverse,
        variants_status=status,
    )

    print(f"✓ captured drill: {filename}  (variants: {status})", file=sys.stderr)
    return 0


def open_in_editor(template: str) -> str | None:
    editor = os.environ.get("EDITOR", "vim")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".drill.txt", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(template)
        path = tmp.name

    try:
        result = subprocess.run([editor, path])
        if result.returncode != 0:
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def parse_template(raw: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    buf: list[str] = []

    def flush() -> None:
        if current:
            sections[current] = "\n".join(buf).strip()

    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            flush()
            current = stripped[1:-1]
            buf = []
            continue
        if current:
            buf.append(line)
    flush()
    return sections


if __name__ == "__main__":
    sys.exit(main())
