# LearnBase - AI Context

An MCP server that enables AI-driven spaced repetition review of markdown notes and lightweight learning topic tracking.

## Core Concept

**Two complementary systems:**

1. **Review Notes** (`~/.learnbase/notes/`): Markdown files with YAML frontmatter for spaced repetition learning
2. **To-Learn Topics** (`~/.learnbase/to_learn.md`): Single markdown file for quick capture and tracking of topics to learn

## Architecture

```
src/learnbase/
├── core/
│   ├── models.py           # Note dataclass with frontmatter serialization
│   ├── note_manager.py     # File I/O for notes directory
│   ├── to_learn_manager.py # Single-file manager for learning topics
│   └── spaced_rep.py       # SM-2 & scheduled review algorithms
├── tools/                  # MCP tool handlers
│   ├── notes.py            # Note CRUD operations
│   ├── review.py           # Review workflow
│   ├── stats.py            # Statistics
│   ├── performance.py      # Session tracking
│   └── to_learn.py         # To-learn topic management
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

## Review Session Protocol

The MCP server works with a Claude Skill at `~/.claude/skills/learnbase/SKILL.md`:

1. AI calls `get_due_notes()` to see what's due
2. AI calls `review_note(filename)` to get note content
3. **Skill conducts review**: Generates 3+ questions, evaluates answers, tracks scores in memory
4. AI calls `record_review(filename, rating)` where rating 1-4 determines next interval:
   - 1 (poor): Reset to 1 day, decrease ease
   - 2 (fair): Half interval, slightly decrease ease
   - 3 (good): Interval × ease_factor
   - 4 (excellent): Interval × 2.5, increase ease
5. AI calls `save_session_history(filename, session_data)` with all question data:
   - Saves session history to JSON
   - Updates question_performance in note frontmatter using EMA
   - Single operation replaces previous per-question saves

## Key Files

**Review Notes:**
- `~/.learnbase/notes/` - Notes storage directory
- `~/.learnbase/notes/README.md` - Auto-generated index
- `~/.learnbase/history/` - Review session history

**To-Learn Topics:**
- `~/.learnbase/to_learn.md` - Single file for all learning topics
- `~/.learnbase/to_learn_archived_*/` - Archived old topic files

**Skills:**
- `~/.claude/skills/learnbase/SKILL.md` - Review protocol for AI

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

## Complementary Workflow

1. **Capture** → `add_to_learn` ("I want to learn about X")
2. **Research** → `update_to_learn` (add notes as you learn)
3. **Solidify** → `add_note` (create spaced repetition note)
4. **Review** → `get_due_notes` + review session
5. **Archive** → `remove_to_learn` (topic learned, now in notes system)
