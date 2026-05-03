# LearnBase - AI Context

An MCP server that enables AI-driven spaced repetition review of markdown notes and lightweight learning topic tracking.

## Core Concept

**Six complementary systems:**

1. **Review Notes** (`~/.learnbase/notes/`): Markdown files with YAML frontmatter for spaced repetition learning
2. **To-Learn Topics** (`~/.learnbase/to_learn.md`): Single markdown file for quick capture and tracking of topics to learn
3. **Semantic Search** (`~/.learnbase/vector_db/`): ChromaDB vector database for finding notes by meaning, not just keywords
4. **Task Management** (`~/.learnbase/tasks.db`): SQLite-backed task tracking with AI-powered categorization and daily workflows
5. **Planning & Context** (`~/.learnbase/tasks.db`): SQLite-backed project/people context with auto-staleness detection and priority-based planning at monthly/weekly/daily zoom levels
6. **Drill Cards** (`~/.learnbase/notes/drill-*.md`): Code flashcards with ladder-based spaced repetition and three review modes (Drill/Buddy/Reverse). For keeping useful-but-infrequent coding skills sharp.

## Architecture

```
src/learnbase/
├── core/
│   ├── models.py           # Note, Task, DailyLog dataclasses with frontmatter serialization
│   ├── note_manager.py     # File I/O for notes directory
│   ├── to_learn_manager.py # Single-file manager for learning topics
│   ├── rag_manager.py      # ChromaDB vector database manager
│   ├── tasks_manager.py    # Task CRUD and query operations
│   ├── daily_manager.py    # Daily workflow management
│   ├── context_manager.py  # SQLite-backed project/people context with staleness
│   ├── planning_manager.py # Priority CRUD and planning workflow aggregation
│   └── spaced_rep.py       # SM-2 & scheduled review algorithms
├── tools/                  # MCP tool handlers
│   ├── notes.py            # Note CRUD operations
│   ├── review.py           # Review workflow
│   ├── stats.py            # Statistics
│   ├── performance.py      # Session tracking
│   ├── to_learn.py         # To-learn topic management
│   ├── rag.py              # Semantic search operations
│   ├── tasks.py            # Task management operations
│   ├── daily.py            # Daily workflow operations
│   ├── context.py          # Context, project, and people operations
│   └── planning.py         # Priority and planning operations
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

**Skills:**
- `~/.claude/skills/learnbase/review.md` - Review session protocol
- `~/.claude/skills/learnbase/capture.md` - Note creation workflow
- `~/.claude/skills/learnbase/to-learn.md` - Topic bookmarking
- `~/.claude/skills/learnbase/monthly-review.md` - Monthly priority setting
- `~/.claude/skills/learnbase/weekly-planning.md` - Weekly planning
- `~/.claude/skills/learnbase/task-capture.md` - Natural language task creation
- `~/.claude/skills/learnbase/daily-start.md` - Morning standup
- `~/.claude/skills/learnbase/daily-end.md` - Evening reflection

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

## Drill Card System

**Purpose:** Keep useful-but-infrequent coding skills (shell one-liners, regex, SQL idioms, language patterns) sharp via short flashcard-style review with spaced repetition.

### Drill Card Model

Drill cards are stored as `drill-*.md` files alongside other notes (same directory, same atomic file writes, same RAG indexing). The body contains `## Prompt` and `## Model Answer` sections; metadata lives in YAML frontmatter.

```python
@dataclass
class DrillNote(Note):
    language: str                                # bash, python, sql, regex, ...
    why_captured: str                            # one-line context for future-you
    tags: List[str]
    review_mode: str = "ladder"                  # always 'ladder' for drills
    ladder_step: int                             # index into [1, 3, 7, 14, 30, 90, 180]
    next_review: datetime
    last_reviewed: Optional[datetime]
    review_count: int
    fail_streak: int                             # consecutive fails; >= 3 → needs_rewrite
    needs_rewrite: bool                          # auto-flagged after 3 first-mode fails
    variants_status: Literal['pending', 'ready', 'failed']
    buddy_variants: List[Dict]                   # [{broken, bug}, ...] — for Buddy mode
    reverse_variants: List[Dict]                 # [{code, correct, issue?}, ...] — for Reverse mode
```

### Three Review Modes (chip tabs in TUI)

| Mode | What you do | Source |
|---|---|---|
| **Drill** | Produce — write the answer from a blank prompt | model_answer (always available) |
| **Buddy** | Repair — given a broken version, produce the fix | buddy_variants (LLM-generated at capture) |
| **Reverse** | Review — judge whether a candidate is correct | reverse_variants (mix of correct/buggy) |

Variants are pre-generated **at capture time** via `core/llm_generator.py` using Claude Haiku 4.5 (default). This keeps review fully scriptable / offline. If `ANTHROPIC_API_KEY` is missing the card still saves with `variants_status='failed'` — Drill mode still works; Buddy/Reverse become available after `regenerate_variants`.

### Ladder Spaced Repetition

Pass/fail only — distinct from the SM-2 spaced/scheduled modes used by ReviewNote. Defined in `core/spaced_rep.py::calculate_ladder_review`.

- Intervals: `[1, 3, 7, 14, 30, 90, 180]` days
- Pass: `step += 1` (capped); `fail_streak = 0`; clears `needs_rewrite`
- Fail: `step -= 1` (floor 0); `fail_streak += 1`; sets `needs_rewrite` at 3
- **Mode-tab rule**: only the *first* mode attempted per card per session updates SR. Other modes are free practice (`is_first_mode=False`).

### MCP Tools

- `add_drill_card` — capture (similarity dedup; LLM variants synchronously)
- `review_drill` — record pass/fail (with `mode` and `is_first_mode`)
- `list_due_drills` — what's due today
- `get_drill` — fetch one with variants
- `regenerate_variants` — retry LLM generation for failed/pending cards

### Capture Paths

- **Claude skill**: `~/.claude/skills/learnbase-drill-capture/SKILL.md` — natural-language capture in chat, calls `add_drill_card`
- **Zsh hotkey**: `scripts/zsh_drill_widget.zsh` binds `Ctrl+X Ctrl+D` — captures the current command line; calls `scripts/capture_drill.py` which opens `$EDITOR` with a template
- **CLI**: `scripts/capture_drill.py [--language LANG] [--prefill-answer "..."]`
- **TUI**: `learnbase-drill` (Bubbletea, retro monochrome neon-yellow palette) — review queue + capture from inside the TUI

### TUI

- Binary: `tui/cmd/learnbase-drill`
- Helper bridge: `tui/helper/learnbase_drill.py` (line-delimited JSON over subprocess stdin/stdout — same pattern as `learnbase_search.py`)
- UI package: `tui/internal/ui/drill/` — phases (Loading/Summary/Attempt/Revealed/Finished), tab-cycling between modes, `Ctrl+E` drops to `$EDITOR` for multi-line input, type-first-lock reveal, pass/fail self-assessment
- Bridge package: `tui/internal/drill/bridge.go` — typed wrapper around the helper

### Key Files

- `src/learnbase/core/models.py::DrillNote` — model + body parser/builder
- `src/learnbase/core/spaced_rep.py::calculate_ladder_review` — ladder SR
- `src/learnbase/core/llm_generator.py` — pluggable variant generator (default Anthropic Haiku 4.5)
- `src/learnbase/tools/drills.py` — five MCP handlers
- `tests/test_ladder_sr.py`, `tests/test_drill_models.py`, `tests/test_drill_tools.py`

### Capture/review workflow

1. Notice a useful command/idiom in real work
2. Capture via zsh `Ctrl+X Ctrl+D`, Claude skill, or TUI `c` key
3. Card saves with LLM-generated Buddy + Reverse variants (sync, ~2-5s)
4. Card is due immediately; appears in `learnbase-drill` queue
5. Review with pass/fail; ladder advances or demotes
6. Three consecutive first-mode fails flags the card for rewrite

## Task Management System

**Purpose:** Intelligent task tracking with AI-powered categorization, active context awareness, and daily workflow management.

### Task Model

```python
@dataclass
class Task:
    id: str                          # e.g., "2026-02-03-call-dan"
    title: str
    description: str                 # Markdown body
    
    # Categorization
    categories: List[str]            # [people, idea, project, admin]
    workspace: str                   # work | personal | contract
    project: Optional[str]           # Link to active-context project
    
    # Scheduling
    due: datetime
    status: str                      # pending | in_progress | completed
    dependencies: List[str]          # Task IDs that block this task
    
    # Metadata
    created: datetime
    updated: datetime
    completed: Optional[datetime]
    
    # Auto-categorization
    confidence: Dict[str, float]     # {workspace: 0.85, project: 0.9, ...}
    reasoning: Optional[str]         # Why LLM chose these categories
```

### MCP Tools

**Task Management:**
- `create_task` - Create task with auto-categorization
- `get_task` - Get task by ID
- `list_tasks` - List tasks with filters (status, workspace, project, categories)
- `update_task` - Update task fields
- `archive_task` - Archive completed task

**Daily Workflow:**
- `create_daily_plan` - Generate morning checklist with priorities
- `update_daily_reflection` - Process evening reflection and update tasks

**Context Awareness:**
- `get_context` - Get projects and people with staleness indicators (SQLite-backed)
- `categorize_task` - Auto-categorize task with staleness-aware confidence scoring
- `add_project` / `update_project` / `archive_project` - Manage project context
- `add_person` / `update_person` / `remove_person` - Manage people context

**Planning:**
- `get_priorities` - List priorities with filters (scope, period, status, project)
- `create_priority` / `update_priority` - Manage monthly/weekly priorities
- `get_planning_context` - Aggregated context for planning conversations
- `save_review` - Save planning review summary as markdown

### Skills

**Task Capture** (`~/.claude/skills/learnbase/task-capture.md`)
- Triggers: "I need to", "I should", "Don't forget to", "Remind me to"
- Natural language task capture
- Reads SQLite-backed project context with staleness awareness
- Confidence scoring (workspace, project, categories, due date)
- Asks clarifying questions if confidence < 0.6 or due date missing

**Monthly Review** (`~/.claude/skills/learnbase/monthly-review.md`)
- Triggers: "monthly review", "monthly planning", "month priorities"
- Pulls all projects, last month's priorities and outcomes
- Socratic conversation to set 2-3 monthly milestone-based priorities
- Writes priorities to DB + summary markdown to `~/.learnbase/reviews/`

**Weekly Planning** (`~/.claude/skills/learnbase/weekly-planning.md`)
- Triggers: "weekly planning", "plan the week", "week priorities"
- Pulls monthly priorities, calendar, tasks, last week's outcomes
- Socratic conversation to set 3-5 weekly priorities + generate linked tasks
- Writes priorities to DB + summary markdown to `~/.learnbase/reviews/`

**Daily Start** (`~/.claude/skills/learnbase/daily-start.md`)
- Triggers: "Let's start the day", "morning routine", "today's tasks"
- Checks for stale projects and prompts refresh (Y/change/archive)
- Flags stale weekly priorities
- Generates daily plan with overdue/today/week tasks
- Shows task-priority-project links
- Creates `~/.learnbase/daily/YYYY-MM-DD.md`

**Daily End** (`~/.claude/skills/learnbase/daily-end.md`)
- Triggers: "Let's end the day", "evening reflection", "wrap up"
- Reviews completed/incomplete tasks
- Gathers reflection notes
- Updates task files with notes
- Rolls over incomplete tasks to tomorrow
- Deletes daily file after processing

### Key Files

**Task Storage:**
- `~/.learnbase/tasks/` - Active tasks directory
- `~/.learnbase/tasks/archive/` - Archived completed tasks
- `~/.learnbase/tasks/README.md` - Task system documentation

**Daily Workflow:**
- `~/.learnbase/daily/` - Daily log files
- `~/.learnbase/daily/README.md` - Daily workflow documentation

**Context & Planning (SQLite in `~/.learnbase/tasks.db`):**
- `projects` table - Active projects with workspace, description, auto-staleness (fresh/stale/inactive)
- `people` table - People with relationship descriptions
- `priorities` table - Monthly/weekly priorities with status tracking
- `~/.learnbase/reviews/` - Human-readable planning review summaries (markdown, not parsed)

### Planning Workflow

1. **Monthly review** (~30 min) → Set 2-3 project milestone priorities for the month
2. **Weekly planning** (~15 min) → Break monthly priorities into 3-5 weekly priorities + tasks
3. **Daily start** → Check stale projects, show tasks with priority context
4. **Task capture** → Ad-hoc tasks auto-linked to priorities where possible
5. **Daily end** → Reflect, update tasks, roll over incomplete
6. **Archive** → Completed tasks moved to archive/

### Task Workflow

1. **Capture** → "I need to call Dan tomorrow" → Natural language capture
2. **Categorize** → Auto-categorize with staleness-aware confidence scoring
3. **Clarify** → Ask questions if confidence < 0.6 or due date missing
4. **Create** → Task in SQLite with optional priority_id link
5. **Morning** → "Let's start the day" → Generate daily plan with priority context
6. **Work** → User completes tasks throughout the day
7. **Evening** → "Let's end the day" → Reflect, update tasks, roll over incomplete
8. **Archive** → Completed tasks moved to archive/

### Task Categorization

**Categories:**
- **people** - Tasks involving other people (calls, meetings, emails)
- **idea** - Ideas to explore, brainstorming tasks
- **project** - Implementation, coding, building tasks
- **admin** - Administrative tasks, reminders, scheduling

**Workspaces:**
- **work** - Work-related tasks
- **personal** - Personal tasks
- **contract** - Contract/freelance work

**Auto-Categorization Logic:**
1. Query projects and people from SQLite (via `ContextManager`)
2. Match project by name, slug, or description words
3. Apply staleness multiplier: fresh=0.9, stale=0.4, inactive=excluded
4. Infer workspace from matched project or keywords
5. Detect categories by text patterns (call→people, implement→project, etc.)
6. Calculate confidence scores (0.0-1.0) for each field
7. Ask clarifying questions if any confidence < 0.6
8. Create task with confidence scores, reasoning, and optional priority_id link

### Development Guidelines

**Task Files:**
- Filenames: `YYYY-MM-DD-slug.md` (due date prefix + slugified title)
- Atomic file writes (temp file + rename)
- YAML frontmatter + markdown body
- Manual editing supported (Obsidian-compatible)

**Daily Files:**
- Created each morning via `create_daily_plan`
- User can manually check off tasks during day
- Deleted after evening reflection (data preserved in task files)
- Temporary workflow files, not archival

**Context (SQLite-backed):**
- Projects and people stored in `~/.learnbase/tasks.db`
- Auto-staleness: projects stale after 14 days without update
- Both Claude and user can add/update/archive via MCP tools
- Stale projects surface in daily-start for quick refresh (Y/change/archive)
- Inactive projects excluded from categorization entirely

**Planning:**
- Priorities table: monthly and weekly scope with period tracking
- Tasks link to priorities via `priority_id` for traceability
- Review summaries saved as markdown in `~/.learnbase/reviews/`
- Graceful degradation: missed reviews trigger catch-up, not failure
