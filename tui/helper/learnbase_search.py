#!/usr/bin/env python3
"""Persistent semantic-search daemon used by the Go TUI.

Reads one JSON request per line from stdin, writes one JSON response per line
to stdout. Reuses the project's existing RAGManager so the ChromaDB collection
and embedding model stay in sync with the MCP server.

Request:  {"query": "...", "limit": 30}
Response: {"results": [{"filename": "...", "title": "...", "similarity": 0.87, "note_type": "review"}, ...]}
Error:    {"error": "message"}
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _resolve_repo_root() -> Path:
    # helper lives at <repo>/tui/helper/learnbase_search.py
    return Path(__file__).resolve().parents[2]


def main() -> int:
    repo_root = _resolve_repo_root()
    sys.path.insert(0, str(repo_root / "src"))

    try:
        from learnbase.core.note_manager import NoteManager
        from learnbase.core.rag_manager import RAGManager
    except Exception as e:
        print(json.dumps({"error": f"import failed: {e}"}), flush=True)
        return 1

    try:
        note_manager = NoteManager()
        rag = RAGManager(note_manager=note_manager)
        if not rag.is_available():
            print(json.dumps({"error": "RAGManager unavailable (ChromaDB not initialised)"}), flush=True)
            return 1
    except Exception as e:
        print(json.dumps({"error": f"init failed: {e}"}), flush=True)
        return 1

    # Signal readiness so the Go side can drop the loading state.
    print(json.dumps({"ready": True}), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            query = req.get("query", "")
            limit = int(req.get("limit", 30))
            if not query:
                print(json.dumps({"results": []}), flush=True)
                continue
            hits = rag.search_notes(query=query, limit=limit)
            payload = {
                "results": [
                    {
                        "filename": h.get("filename"),
                        "title": h.get("title"),
                        "similarity": h.get("similarity"),
                        "note_type": h.get("note_type"),
                    }
                    for h in hits
                ]
            }
            print(json.dumps(payload), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
