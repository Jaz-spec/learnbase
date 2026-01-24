# LearnBase Skills

This directory contains skill files that guide your AI agent through specific LearnBase workflows.

## Available Skills

### `/quiz` - Interactive Review Sessions
Conducts Socratic, conversational review sessions using spaced repetition.

**What it does:**
- Generates thoughtful questions from your notes
- Uses the Socratic method to help you discover answers
- Tracks which concepts you're struggling with
- Adapts questions based on your previous performance

**Usage:**
```
"quiz me"
"what should I review today?"
"let's revise my notes"
```

See the main README for details on how reviews work.

### `/verify` - Note Validation and Research
Researches your notes to verify accuracy, find authoritative sources, and assign confidence scores.

**What it does:**
- Searches for authoritative sources (official docs, academic papers, etc.)
- Verifies claims against primary sources
- Assigns confidence scores (0.0-1.0) based on source quality
- Suggests specific amendments when needed

**Usage:**
```
"validate this note"
"what needs verifying?"
"find sources for [topic]"
```

## Setup

These skills are designed to work with Claude Code. To install:

**Option 1: Ask Claude to do it** (easiest)
```
"Can you copy the skills from this project to my ~/.claude/skills/ directory?"
```

**Option 2: Do it manually**
```bash
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

For other AI agents, you may need to adjust the skill instructions slightly depending on your agent's conversational style.

## How Skills Work

Skills are instruction files that tell your AI agent how to perform specific tasks. Once the skill is loaded:
- The AI follows the skill's workflow step-by-step
- All interaction happens in your chat (minimal MCP tool calls)
- The AI adapts based on your responses while following the skill's principles

Think of them as detailed playbooks for your AI.
