# LearnBase - AI Context

An MCP server that enables AI-driven spaced repetition review of markdown notes.

## Core Concept

Notes are markdown files with YAML frontmatter stored in `~/.learnbase/notes/`. The MCP server exposes tools that let AI conduct Socratic review sessions using the SM-2 spaced repetition algorithm.

## Architecture

```
src/learnbase/
├── core/
│   ├── models.py         # Note dataclass with frontmatter serialization
│   ├── note_manager.py   # File I/O for notes directory
│   └── spaced_rep.py     # SM-2 & scheduled review algorithms
├── tools/               # MCP tool handlers (notes, review, stats, performance)
└── mcp_server.py        # MCP server registration
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

**Note Management**: add_note, get_note, list_notes, edit_note, delete_note

**Review Workflow**:
1. `get_due_notes()` - List notes due today
2. `review_note(filename)` - Fetch note content (Skill generates questions)
3. `record_review(filename, rating)` - Update SM-2 schedule based on rating (1-4)

**Analytics**: get_stats, calculate_next_review

**Performance Tracking**: save_session_history

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

- `~/.learnbase/notes/` - Notes storage directory
- `~/.learnbase/notes/README.md` - Auto-generated index
- `~/.claude/skills/learnbase/SKILL.md` - Review protocol for AI

## Development Guidelines

- Notes are the source of truth (not database)
- All dates use ISO 8601 format
- Filenames are lowercase with hyphens: `python-gil.md`
- The Skill handles question generation; MCP tools only manage state
- Question performance uses exponential moving average (70% new, 30% old)
