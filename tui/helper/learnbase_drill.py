#!/usr/bin/env python3
"""Persistent drill-card helper used by the Go TUI.

Reads one JSON request per line from stdin, writes one JSON response per line
to stdout. Reuses the Python NoteManager so files, indexing, and SR stay in
sync with the MCP server.

Protocol — every request has an "op" field:
  {"op": "list_due", "limit": 50}                              → {"drills": [...]}
  {"op": "get", "filename": "drill-foo.md"}                    → {"drill": {...}}
  {"op": "review", "filename": "...", "passed": true,
                     "mode": "drill", "is_first_mode": true}     → {"drill": {...updated...}}
  {"op": "add", "title": "...", "prompt": "...",
                  "model_answer": "...", "language": "bash",
                  "why_captured": "...", "tags": [...],
                  "force": false, "skip_variants": false}        → {"created": "filename"} | {"similar": [...]}
  {"op": "find_similar", "prompt": "..."}                      → {"matches": [...]}
  {"op": "regenerate", "filename": "..."}                      → {"drill": {...}} | {"error": "..."}

Errors:
  {"error": "message"}
"""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    repo_root = _resolve_repo_root()
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from learnbase.core.note_manager import NoteManager
        from learnbase.core.rag_manager import RAGManager
        from learnbase.core.models import DrillNote
        from learnbase.core.llm_generator import generate_variants, LLMUnavailableError
    except Exception as e:
        print(json.dumps({"error": f"import failed: {e}"}), flush=True)
        return 1

    try:
        note_manager = NoteManager()
        # Best-effort RAG init for similarity dedup.
        try:
            rag = RAGManager(note_manager=note_manager)
            note_manager.rag_manager = rag
        except Exception:
            pass
    except Exception as e:
        print(json.dumps({"error": f"init failed: {e}"}), flush=True)
        return 1

    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            op = req.get("op")
            resp = _dispatch(note_manager, DrillNote, generate_variants, LLMUnavailableError, op, req)
        except Exception as e:
            resp = {"error": f"{e}\n{traceback.format_exc()}"}
        print(json.dumps(resp, default=_json_default), flush=True)

    return 0


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"{type(obj).__name__} not JSON serialisable")


def _serialise_drill(note: Any) -> Dict[str, Any]:
    prompt, model_answer = note.parse_prompt_and_answer()
    return {
        "filename": note.filename,
        "title": note.title,
        "language": note.language,
        "tags": note.tags,
        "why_captured": note.why_captured,
        "prompt": prompt,
        "model_answer": model_answer,
        "ladder_step": note.ladder_step,
        "next_review": note.next_review.isoformat(),
        "last_reviewed": note.last_reviewed.isoformat() if note.last_reviewed else None,
        "review_count": note.review_count,
        "fail_streak": note.fail_streak,
        "needs_rewrite": note.needs_rewrite,
        "variants_status": note.variants_status,
        "buddy_variants": note.buddy_variants,
        "reverse_variants": note.reverse_variants,
    }


def _dispatch(nm, DrillNote, generate_variants, LLMUnavailableError, op, req):
    if op == "list_due":
        limit = req.get("limit")
        drills = nm.get_due_drills(limit=limit)
        return {"drills": [_serialise_drill(d) for d in drills]}

    if op == "get":
        filename = req.get("filename")
        if not filename:
            return {"error": "filename required"}
        note = nm.get_note(filename)
        if not note or not isinstance(note, DrillNote):
            return {"error": f"drill {filename} not found"}
        return {"drill": _serialise_drill(note)}

    if op == "review":
        filename = req.get("filename")
        passed = bool(req.get("passed", False))
        is_first_mode = bool(req.get("is_first_mode", True))
        if not filename:
            return {"error": "filename required"}
        note = nm.update_drill_review(
            filename=filename, passed=passed, is_first_mode=is_first_mode
        )
        return {"drill": _serialise_drill(note)}

    if op == "find_similar":
        prompt = req.get("prompt", "")
        matches = nm.find_similar_drills(prompt=prompt, threshold=0.75, limit=3)
        return {"matches": matches}

    if op == "add":
        required = ["title", "prompt", "model_answer", "language"]
        missing = [k for k in required if not req.get(k)]
        if missing:
            return {"error": f"missing: {', '.join(missing)}"}

        force = bool(req.get("force", False))
        skip_variants = bool(req.get("skip_variants", False))

        if not force:
            similar = nm.find_similar_drills(
                prompt=req["prompt"], threshold=0.75, limit=3
            )
            if similar:
                return {"similar": similar}

        buddy_variants, reverse_variants = [], []
        variants_status = "pending"
        if not skip_variants:
            try:
                result = generate_variants(
                    prompt=req["prompt"],
                    model_answer=req["model_answer"],
                    language=req["language"],
                )
                buddy_variants = result["buddy"]
                reverse_variants = result["reverse"]
                variants_status = "ready"
            except LLMUnavailableError:
                variants_status = "failed"
            except Exception:
                variants_status = "failed"

        filename = nm.create_drill_note(
            title=req["title"],
            prompt=req["prompt"],
            model_answer=req["model_answer"],
            language=req["language"],
            why_captured=req.get("why_captured", ""),
            tags=req.get("tags") or [],
            buddy_variants=buddy_variants,
            reverse_variants=reverse_variants,
            variants_status=variants_status,
        )
        return {"created": filename, "variants_status": variants_status}

    if op == "regenerate":
        filename = req.get("filename")
        if not filename:
            return {"error": "filename required"}
        note = nm.get_note(filename)
        if not note or not isinstance(note, DrillNote):
            return {"error": f"drill {filename} not found"}
        prompt, model_answer = note.parse_prompt_and_answer()
        try:
            result = generate_variants(
                prompt=prompt, model_answer=model_answer, language=note.language
            )
        except LLMUnavailableError as e:
            return {"error": f"LLM unavailable: {e}"}
        except Exception as e:
            return {"error": f"LLM failed: {e}"}
        nm.update_drill_variants(
            filename=filename,
            buddy_variants=result["buddy"],
            reverse_variants=result["reverse"],
            variants_status="ready",
        )
        return {"drill": _serialise_drill(nm.get_note(filename))}

    return {"error": f"unknown op: {op}"}


if __name__ == "__main__":
    sys.exit(main())
