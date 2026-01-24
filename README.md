# LearnBase
## Overview

Learnbase is a quiz / note reviewing tool that consists of 3 parts:
- a learnbase directory where you store all of your notes in md files
- an mcp server that handles the file operations for these notes
- skills files that prompt an LLM to carry out socratic quizzes and verify note accuracy with research

The benefit of this is that the mcp server ensures reliable and controllable interactions with your notes (i.e. Your agent won't accidentally delete everything). The skills file means that once your agent has retrieved your notes data, the rest of the interaction exists just in your chat (so you're not making endless MCP tool calls).

## Notes on the setup

This tool was built and tested with Claude Code. However it is intended to be set up easily with any terminal agent (although the skills file may need tweaking here and there depending on which agent you end up using. For example, Gemini I found was a little less conversational than Claude and may need some extra prompting) 

It can be implemented with desktop instances but skills are less compatible here (atleast with anthropic) so as a work around you could simply copy or link the skills folder in as a prompt in your chat/project.

## Quick Start

### 1. Install LearnBase

```bash
# Clone the repository
git clone https://github.com/username/learnbase.git
cd learnbase

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install the MCP server
pip install -e .
```

This installs the LearnBase MCP server that Claude will use to manage your notes.

### 2. Set Up the MCP Server
#### For the terminal (Claude Code)

**Option 1: Ask Claude to configure it** (easiest)

After installing LearnBase, just ask Claude Code:
```
"Can you configure the LearnBase MCP server in my ~/.claude.json file?"
```

**Option 2: Manual setup**

Edit your `~/.claude.json` file and add the LearnBase MCP server configuration:

```json
{
  "mcpServers": {
    "learnbase": {
      "type": "stdio",
      "command": "/absolute/path/to/learnbase/venv/bin/python",
      "args": ["-m", "learnbase.mcp_server"],
      "env": {}
    }
  }
}
```

**Important**:
- Replace `/absolute/path/to/learnbase` with where you cloned LearnBase
- Make sure you've activated your venv and run `pip install -e .` first (see step 1)
- If `mcpServers` already exists in your config, just add the `learnbase` entry inside it

**Verify it works:**
```
# Restart Claude Code, then ask:
"Can you list my notes?"
```

If Claude can access the LearnBase tools, you're all set!

#### For desktop 
Add this to your Claude Desktop config at `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "learnbase": {
      "command": "/absolute/path/to/learnbase/venv/bin/python",
      "args": ["-m", "learnbase.mcp_server"]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/learnbase` with where you actually put LearnBase.


### 3. Add the Skills

The `skills/` directory contains two skills that teach your AI how to work with LearnBase:
- **quiz** - Conducts Socratic review sessions
- **verify** - Researches and validates note accuracy with sources

**Option 1: Ask Claude to do it** (easiest)
```
"Can you copy the skills from this project to my ~/.claude/skills/ directory?"
```

**Option 2: Do it manually**
```bash
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

See `skills/README.md` for detailed documentation on each skill.

## Getting Started

Now that LearnBase is set up, here's how to use it:

1. **Add your first note**: Just talk to Claude about something you're learning
   "Can you create a note about Python decorators for me?"

2. **Review your notes**: When notes are due, ask:
   "What should I review today?" or "quiz me!"

3. **Verify note accuracy**: Research and add sources to your notes:
   "What needs verifying?" or "validate this note"

4. **Check your progress**:
   "Show me my learning statistics"

See the sections below for detailed workflows and features.

## The review
### Review Workflow
1. "What should I review?" -> `get_due_notes` to get all the notes that need reviewing
2. User selects the note they want to review -> `review_note` to fetch the note content
3. *[Skill conducts the interactive review]*
4. `record_review` - Save your rating and update schedule

### During the review
#### Asking further questions
You can ask questions at any point during the conversation and the model will automatically carry on with the review once you've said everything has been clarified. 
It will also ask you if you have any questions when it scores your answer. 

At the end of the session, you will be asked if you want to add anything you learned to this note, or to create a new note and store the information there. 

#### Question scores
Based on your answer, each question is given an ID and a percentage score. This means that if you struggle on a question, or ask to prioritise a question or key concept on the next review, this will be recorded with your note. Essential, the quiz tool is adaptive and should ask you increasingly more relevant questions on your notes based on your previous answers.

#### Priority requests
You can explicitly ask to focus on specific topics in your next review session. Just say something like:
- "I'd like to prioritize decorators next time"
- "Can we focus on async/await in the next session?"
- "I want to drill down on memory management"

The system will track these requests and automatically include questions on those topics in your next review. After you've been quizzed on a priority topic twice, it's automatically removed from your priority list. This works alongside the automatic prioritization of questions you've struggled with.

#### Understanding Ratings

At the end of each review, you rate your overall confidence:

- **1 (Poor)** - "I don't get this at all" → Review tomorrow
- **2 (Fair)** - "Sort of getting it" → Review in a few days
- **3 (Good)** - "I understand this well" → Review in 1-2 weeks
- **4 (Excellent)** - "I could teach this" → Much longer interval

The system learns your pace and adjusts intervals automatically using the SM-2 algorithm.

## Validating notes

LearnBase includes a verification system to help you ensure your notes are accurate and well-sourced.

### How it works
The verify skill researches your notes to:
- Find authoritative sources (official docs, academic papers, etc.)
- Verify claims against primary sources
- Assign confidence scores (0.0-1.0) based on source quality
- Suggest specific amendments when needed

### Usage
```
"What needs verifying?" - See unverified notes
"Validate this note" - Research and verify a specific note
"Find sources for [topic]" - Research a note about a topic
```

After validation, the skill will:
1. Show you the sources it found and confidence score
2. Suggest any amendments to improve accuracy
3. Ask if you want to update the note with sources and changes

Notes with low confidence scores are flagged in your note list, so you can prioritize improving them.

## Adding and managing notes
### Adding Notes
After a conversation with Claude you can ask:
```
"Can you make a note of that"
OR
"Can you write a summary of this chat in my notes"
```
You can also ask Claude to create notes from articles, videos, or anything else you're learning about.

Claude will automatically save your notes to be reviewed on a spaced repetition basis, so the next time you review a specific note is generated at the end of the session based on your score and your confidence. 
If you prefer fixed intervals instead of adaptive scheduling, you can ask Claude to create scheduled reviews for your note e.g. once a month. 

### Managing notes
You can ask Claude
```
"Show me all my notes"
"Do I have any notes to review?"
"Show me my review statistics"
```

## The MCP Tools

LearnBase exposes these tools to Claude:

### Note Management
- `add_note` - Create a new note
- `get_note` - Read a specific note
- `list_notes` - See all your notes
- `edit_note` - Update content
- `delete_note` - Remove a note

### Analytics
- `get_stats` - See your progress stats
- `calculate_next_review` - Preview when something will be due

### Performance Tracking
- `save_session_history` - Saves complete review session (questions, scores, timeline)
- This updates question performance automatically using an exponential moving average

## Your notes
Each note is just markdown with YAML frontmatter:

```markdown
---
title: "Python's Global Interpreter Lock"
created: 2025-12-16T10:30:00
review_mode: spaced
next_review: 2025-12-17T10:30:00
interval_days: 1
ease_factor: 2.5
review_count: 0
confidence_score: 0.85
sources:
  - url: "https://docs.python.org/3/c-api/init.html#thread-state-and-the-global-interpreter-lock"
    title: "Python Documentation - GIL"
    accessed_date: "2025-12-16"
---

# Python's Global Interpreter Lock

The GIL is a mutex that protects access to Python objects...
```

## Directory Architecture

LearnBase has two main directories:

### Project Directory
Where you clone the repository:
```
learnbase/                    # Your git clone location
├── src/learnbase/           # Python package source code
│   ├── mcp_server.py       # MCP server entry point
│   ├── core/               # Core models and algorithms
│   │   ├── models.py       # Note dataclass with YAML frontmatter
│   │   ├── note_manager.py # File I/O for notes
│   │   └── spaced_rep.py   # SM-2 spaced repetition algorithm
│   └── tools/              # MCP tool handlers
│       ├── notes.py        # Note CRUD operations
│       ├── review.py       # Review workflow
│       ├── stats.py        # Analytics
│       └── performance.py  # Question performance tracking
├── skills/                 # AI agent skill files
│   ├── README.md          # Skills documentation
│   ├── quiz/              # Review session skill
│   │   └── SKILL.md
│   └── verify/            # Note validation skill
│       └── SKILL.md
├── pyproject.toml          # Package configuration
└── README.md              # This file
```

### User Data Directory
Automatically created at `~/.learnbase/`:
```
~/.learnbase/
├── notes/                 # Your learning notes (markdown files)
│   ├── README.md         # Auto-generated index
│   ├── python-gil.md     # Example note
│   └── ...
└── history/              # Review session history (JSON files)
    └── python-gil-2025-01-09-session-abc123.json
```

**This directory is created automatically** when you first use LearnBase. You don't need to configure anything!

## Contributing
PRs welcome!

## License
MIT 

## Credits
Built on the SM-2 spaced repetition algorithm (the one Anki uses) and the MCP (Model Context Protocol) framework from Anthropic.

---
