# LearnBase

> **Work in progress.** This is a prototyping repo — the goal is to discover what the feature set should look like through trial and error, not to produce production-ready code. Browse it for ideas, but it's not intended for a polished install-and-run experience.

## What is it?

An MCP server that gives AI agents (Claude Code, etc.) tools for knowledge management, spaced repetition, task tracking, and daily workflows.

## Features

### Spaced Repetition Notes
Markdown notes with YAML frontmatter, reviewed on an adaptive schedule (SM-2 algorithm). AI conducts Socratic review sessions — asking questions, scoring answers, and adjusting intervals. Questions you struggle with get asked more often.

### Semantic Search
ChromaDB vector database indexes your notes for natural language search. Find related notes by meaning, not just keywords.

### To-Learn Topics
Quick-capture backlog for things you want to learn later. Track progress from "to-learn" through "in-progress" to "learned", then promote to a full review note.

### Task Management
AI-powered task capture and categorization. Reads your active project context to auto-categorize by workspace (work/personal/contract), project, and type (people/idea/project/admin). Confidence scoring asks clarifying questions only when unsure.

### Daily Workflows
Morning standup generates a prioritised overview of tasks, calendar events, and overdue items. Evening reflection captures notes on completed work, rolls over incomplete tasks, and cleans up.

### Google Calendar Integration
Fetches today's events and presents them in the morning standup. Pairs with the notification daemon for desktop reminders.

### Calendar Notification Daemon
Dockerised scheduler that sends macOS desktop notifications for calendar events. A container handles timing, a host-side listener triggers OS alerts. Lifecycle managed by bash scripts, started/stopped automatically during daily workflows. See `docs/docker-setup-guide.md`.

### Note Validation
Research and verify note accuracy against primary sources. Assigns confidence scores and suggests amendments.

## Architecture

```
src/learnbase/
├── core/                    # Domain logic
│   ├── models.py            # Note, Task, DailyLog dataclasses
│   ├── note_manager.py      # Note file I/O
│   ├── to_learn_manager.py  # Learning topic tracking
│   ├── rag_manager.py       # ChromaDB vector search
│   ├── tasks_manager.py     # Task CRUD and queries
│   ├── daily_manager.py     # Daily workflow management
│   ├── calendar_manager.py  # Google Calendar API
│   ├── context_parser.py    # Active context for categorization
│   └── spaced_rep.py        # SM-2 algorithm
├── tools/                   # MCP tool handlers
│   ├── notes.py             # Note CRUD
│   ├── review.py            # Review sessions
│   ├── to_learn.py          # Topic backlog
│   ├── rag.py               # Semantic search
│   ├── tasks.py             # Task management
│   ├── daily.py             # Daily workflows
│   ├── calendar.py          # Calendar events
│   ├── context.py           # Categorization
│   ├── stats.py             # Analytics
│   └── performance.py       # Session tracking
└── mcp_server.py            # Tool registration

docker/
├── Dockerfile               # Notification daemon image
└── notify-daemon.py         # In-container scheduler

scripts/
├── notify-start.sh          # Start notification daemon + listener
├── notify-stop.sh           # Stop daemon + listener
├── notify-host-listener.py  # Host-side HTTP → macOS alert bridge
└── parse_commits.py         # Git commit parser for project context

skills/
├── quiz/                    # Socratic review session protocol
└── verify/                  # Note validation protocol
```

### User Data (`~/.learnbase/`)

```
~/.learnbase/
├── notes/                   # Review, reference, and evergreen notes
├── history/                 # Review session history (JSON)
├── tasks/                   # Active tasks (markdown)
│   └── archive/             # Completed tasks
├── daily/                   # Daily plan files (temporary)
├── to_learn.md              # Learning topic backlog
├── active-context/          # Project tracking with commit history
│   └── index.md             # Context for AI categorization
└── vector_db/               # ChromaDB persistent storage
```

## Setup

### Install

```bash
git clone https://github.com/Jaz-spec/learnbase.git
cd learnbase
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Configure MCP

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "learnbase": {
      "type": "stdio",
      "command": "/absolute/path/to/learnbase/venv/bin/python",
      "args": ["-m", "learnbase.mcp_server"]
    }
  }
}
```

### Add Skills

```bash
cp -r skills/* ~/.claude/skills/
```

## Credits

Built on the SM-2 spaced repetition algorithm and Anthropic's Model Context Protocol (MCP).

## License

MIT
