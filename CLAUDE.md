# LearnBase - AI Context

An MCP server that enables AI-driven spaced repetition review of markdown notes and lightweight learning topic tracking.

## Core Concept

**Three complementary systems:**

1. **Review Notes** (`~/.learnbase/notes/`): Markdown files with YAML frontmatter for spaced repetition learning
2. **To-Learn Topics** (`~/.learnbase/to_learn.md`): Single markdown file for quick capture and tracking of topics to learn
3. **Semantic Search** (`~/.learnbase/vector_db/`): ChromaDB vector database for finding notes by meaning, not just keywords

## Architecture

```
src/learnbase/
├── core/
│   ├── models.py           # Note dataclass with frontmatter serialization
│   ├── note_manager.py     # File I/O for notes directory
│   ├── to_learn_manager.py # Single-file manager for learning topics
│   ├── rag_manager.py      # ChromaDB vector database manager
│   └── spaced_rep.py       # SM-2 & scheduled review algorithms
├── tools/                  # MCP tool handlers
│   ├── notes.py            # Note CRUD operations
│   ├── review.py           # Review workflow
│   ├── stats.py            # Statistics
│   ├── performance.py      # Session tracking
│   ├── to_learn.py         # To-learn topic management
│   └── rag.py              # Semantic search operations
└── mcp_server.py           # MCP server registration
```

## Note Model

```python
@dataclass
class Note:
    filename: str                           # e.g., "python-gil.md"
    title: str
    body: str                               # Markdown content
    review_mode: str                        # 'spaced' | 'scheduled'

    # SM-2 metadata
    next_review: datetime
    interval_days: int
    ease_factor: float                      # 1.3-3.0
    review_count: int

    # Question tracking
    question_performance: Dict[str, float]  # question_hash -> EMA score
    priority_questions: List[str]           # worst to best
```

## MCP Tools

### Review Notes System

**Note Management**: add_note, get_note, list_notes, edit_note, delete_note

**Review Workflow**:
1. `get_due_notes()` - List notes due today
2. `review_note(filename)` - Fetch note content (Skill generates questions)
3. `record_review(filename, rating)` - Update SM-2 schedule based on rating (1-4)

**Analytics**: get_stats, calculate_next_review

**Performance Tracking**: save_session_history

### To-Learn Topics System

**Topic Management**: add_to_learn, list_to_learn, get_to_learn, update_to_learn, update_to_learn_status, remove_to_learn

**Workflow**:
1. Quick capture: "I'd like to learn about X later" → `add_to_learn(topic="X", context="...")`
2. Track progress: `update_to_learn_status(topic="X", status="in-progress")`
3. Add notes: `update_to_learn(topic="X", notes="Research findings...")`
4. Complete: `update_to_learn_status(topic="X", status="learned")` → `remove_to_learn(topic="X")`

**Statuses**: `to-learn`, `in-progress`, `learned`

### Semantic Search System

**RAG Operations**: index_note, search_notes, remove_from_index, reindex_all_notes, get_index_stats

**Workflow**:
1. Index notes: `reindex_all_notes()` - Build vector database from all notes (review, reference, evergreen)
2. Search: `search_notes(query="concurrency in Python")` - Natural language semantic search
3. Get results with similarity scores, types, confidence, source counts
4. Manual indexing: Only explicit calls to index (no auto-index on creation)

**Technology**:
- **Vector DB**: ChromaDB with persistent storage
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) by default, OpenAI optional
- **Search**: Cosine similarity for semantic matching
- **Metadata**: Flexible schema allows expansion without re-indexing

## Review Session Protocol

The MCP server works with three specialized Claude Skills:

1. **Review Skill** (`~/.claude/skills/learnbase/review.md`)
   - Conducts Socratic review sessions with spaced repetition
   - Uses: `get_due_notes()`, `review_note()`, `record_review()`, `save_session_history()`

2. **Capture Skill** (`~/.claude/skills/learnbase/capture.md`)
   - Creates well-structured notes with proper linking and tagging
   - Uses: `add_note()`, `edit_note()`, `get_note()`

3. **To-Learn Skill** (`~/.claude/skills/learnbase/to-learn.md`)
   - Manages learning topic backlog and tracks progress
   - Uses: `add_to_learn()`, `list_to_learn()`, `update_to_learn()`, `remove_to_learn()`

These skills are loaded on-demand when users trigger relevant phrases. See skill files for detailed protocols.

## Key Files

**Review Notes:**
- `~/.learnbase/notes/` - Notes storage directory
- `~/.learnbase/notes/README.md` - Auto-generated index
- `~/.learnbase/history/` - Review session history

**To-Learn Topics:**
- `~/.learnbase/to_learn.md` - Single file for all learning topics
- `~/.learnbase/to_learn_archived_*/` - Archived old topic files

**Semantic Search:**
- `~/.learnbase/vector_db/` - ChromaDB persistent storage
- Indexed: All note types (review, reference, evergreen)
- Embeddings: 384-dimensional vectors (all-MiniLM-L6-v2)

**Active Context (Project Tracking):**
- `~/.learnbase/active-context/` - Project tracking directory
- `~/.learnbase/active-context/*.md` - Project files with commit history
- `~/.learnbase/active-context/archive/` - Completed projects
- `scripts/parse_commits.py` - Git commit parser (terminal-callable)

**Skills:**
- `~/.claude/skills/learnbase/review.md` - Review session protocol
- `~/.claude/skills/learnbase/capture.md` - Note creation workflow
- `~/.claude/skills/learnbase/to-learn.md` - Topic bookmarking

## Development Guidelines

**General:**
- Markdown files are the source of truth (not database)
- All dates use ISO 8601 format
- Atomic file writes (temp file + rename) to prevent corruption

**Review Notes:**
- Filenames are lowercase with hyphens: `python-gil.md`
- The Skill handles question generation; MCP tools only manage state
- Question performance uses exponential moving average (70% new, 30% old)

**To-Learn Topics:**
- Single file with table (quick topics) and sections (detailed topics)
- Topics can be quick-captured or detailed with notes
- Archive section preserves learning history
- Manual editing supported (Obsidian-friendly)

**Semantic Search:**
- Manual indexing only (explicit user control)
- Whole-note embedding (title + body as single document)
- Metadata supports filtering by note type, confidence, source count
- Local embeddings by default (no API keys required)
- OpenAI embeddings optional (requires OPENAI_API_KEY env var)

**Active Context:**
- Terminal-callable script (no MCP integration yet)
- Plain markdown files (no YAML frontmatter)
- Week-based commit grouping
- Atomic file writes
- Manual editing supported (Obsidian-compatible)

## Complementary Workflow

1. **Capture** → `add_to_learn` ("I want to learn about X")
2. **Research** → `update_to_learn` (add notes as you learn)
3. **Solidify** → `add_note` (create spaced repetition note)
4. **Index** → `index_note` or `reindex_all_notes` (build vector database)
5. **Discover** → `search_notes` (find related notes semantically)
6. **Review** → `get_due_notes` + review session
7. **Archive** → `remove_to_learn` (topic learned, now in notes system)
