"""Data models for LearnBase."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Literal, cast
from pathlib import Path
import re
import frontmatter

from .parsers import (
    parse_datetime,
    parse_review,
    parse_int,
    parse_float,
    parse_optional_float,
    parse_list,
    parse_dict,
    parse_categories,
    parse_workspace,
    parse_confidence
)

# These control how quickly the performance metric adapts to new scores
# Higher new weight = faster adaptation to recent performance
# Lower new weight = more stability, slower to reflect improvemen
EMA_NEW_WEIGHT = 0.7  # Weight given to the new score
EMA_OLD_WEIGHT = 0.3  # Weight given to the previous average

# ================================================================
# NOTE - Parent class
# ================================================================
@dataclass
class Note:
    """Base class for a note"""
    filename: str
    title: str
    body: str

    def _get_metadata(self) -> dict:
        """Override in child classes to provide metadata for serialization."""
        raise NotImplementedError("Child classes must implement _get_metadata")

    @classmethod
    def from_markdown_file(cls, filepath: Path) -> 'Note':
        """
        Create a Note from a markdown file with YAML frontmatter.

        Args:
            filepath: Path to the markdown file

        Returns:
            Note instance (either ReviewNote or ReferenceNote)
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        note_type = post.get('type', 'review')

        if note_type == 'drill':
            now = datetime.now()
            created_at = parse_datetime(post.get('created'), now)
            last_reviewed = parse_review(post.get('last_reviewed'))
            next_review = parse_datetime(post.get('next_review'), now)

            return DrillNote(
                filename=filepath.name,
                title=str(post.get('title', filepath.stem.replace('-', ' ').title())),
                body=str(post.content),
                language=str(post.get('language', 'text')),
                tags=cast(List[str], parse_list(post.get('tags'))),
                why_captured=str(post.get('why_captured', '')),
                sources=cast(List[Dict[str, str]], parse_list(post.get('sources'))),
                created_at=created_at,
                last_reviewed=last_reviewed,
                next_review=next_review,
                ladder_step=parse_int(post.get('ladder_step'), 0),
                review_count=parse_int(post.get('review_count'), 0),
                fail_streak=parse_int(post.get('fail_streak'), 0),
                needs_rewrite=bool(post.get('needs_rewrite', False)),
                variants_status=cast(
                    Literal['pending', 'ready', 'failed'],
                    post.get('variants_status', 'pending')
                ),
                buddy_variants=cast(List[Dict[str, Any]], parse_list(post.get('buddy_variants'))),
                reverse_variants=cast(List[Dict[str, Any]], parse_list(post.get('reverse_variants'))),
            )
        elif note_type == 'reference':
            now = datetime.now()
            created_at = parse_datetime(post.get('created'), now)

            return ReferenceNote(
                filename=filepath.name,
                title=str(post.get('title', filepath.stem.replace('-', ' ').title())),
                body=str(post.content),
                created_at=created_at,
                confidence_score=parse_optional_float(post.get('confidence_score')),
                sources=cast(List[Dict[str, str]], parse_list(post.get('sources')))
            )
        elif note_type == 'evergreen':
            now = datetime.now()
            created_at = parse_datetime(post.get('created'), now)

            return EvergreenNote(
                filename=filepath.name,
                title=str(post.get('title', filepath.stem.replace('-', ' ').title())),
                body=str(post.content),
                created_at=created_at,
                confidence_score=parse_optional_float(post.get('confidence_score')),
                sources=cast(List[Dict[str, str]], parse_list(post.get('sources')))
            )
        else:

            now = datetime.now()
            created_at = parse_datetime(post.get('created'), now)
            last_reviewed = parse_review(post.get('last_reviewed'))
            next_review = parse_datetime(post.get('next_review'), now)

            return ReviewNote(
                filename=filepath.name,
                title=str(post.get('title', filepath.stem.replace('-', ' ').title())),
                body=str(post.content),
                review_mode=cast(Literal['spaced', 'scheduled'], post.get('review_mode', 'spaced')),
                schedule_pattern=cast(Optional[str], post.get('schedule_pattern')),
                created_at=created_at,
                last_reviewed=last_reviewed,
                next_review=next_review,
                interval_days=parse_int(post.get('interval_days'), 1),
                ease_factor=parse_float(post.get('ease_factor'), 2.5),
                review_count=parse_int(post.get('review_count'), 0),
                question_performance=cast(Dict[str, float], parse_dict(post.get('question_performance'))),
                priority_questions=cast(List[str], parse_list(post.get('priority_questions'))),
                last_session_summary=cast(Dict[str, Any], parse_dict(post.get('last_session_summary'))),
                learned_content_count=parse_int(post.get('learned_content_count'), 0),
                priority_requests=cast(List[Dict[str, Any]], parse_list(post.get('priority_requests'))),
                confidence_score=parse_optional_float(post.get('confidence_score')),
                sources=cast(List[Dict[str, str]], parse_list(post.get('sources')))
            )

    def to_markdown_file(self) -> str:
        """
        Convert Note to markdown file content with YAML frontmatter.

        Returns:
            String containing the complete markdown file
        """
        metadata = self._get_metadata()

        post = frontmatter.Post(self.body, **metadata)
        return frontmatter.dumps(post)

    @staticmethod
    def create_filename(title: str) -> str:
        """
        Create a safe filename from a title.

        Args:
            title: Note title

        Returns:
            Safe filename (lowercase, hyphens, .md extension)
        """
        # Remove special characters and convert to lowercase
        safe_title = ''.join(c if c.isalnum() or c.isspace() else '' for c in title)
        # Replace spaces with hyphens
        filename = '-'.join(safe_title.lower().split())
        # Limit length
        if len(filename) > 50:
            filename = filename[:50]
        return f"{filename}.md"

# ================================================================
# REFERENCE - Child class
# ================================================================
@dataclass
class ReferenceNote(Note):
    """Reference note - not being used for spaced repetition"""

    type: str = "reference"

    # Metadata fields (same as ReviewNote for consistency)
    created_at: datetime = field(default_factory=datetime.now)
    confidence_score: Optional[float] = None
    sources: List[Dict[str, str]] = field(default_factory=list)
    # Structure: [{"url": str, "title": str (optional), "accessed_date": str (optional), "note": str (optional)}]

    def _get_metadata(self) -> dict:
        return {
            'title': self.title,
            'type': self.type,
            'created': self.created_at.isoformat(),
            'confidence_score': self.confidence_score,
            'sources': self.sources
        }

    def set_confidence_score(self, score: float):
        """
        Set confidence score with validation.

        Args:
            score: Confidence score (0.0-1.0)

        Raises:
            ValueError: If score is invalid
        """
        if not isinstance(score, (int, float)):
            raise ValueError(f"Confidence score must be numeric, got {type(score).__name__}")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {score}")

        self.confidence_score = score


# ================================================================
# EVERGREEN - Child class
# ================================================================
@dataclass
class EvergreenNote(Note):
    """Evergreen note - manually curated by user; LLMs can read but not edit"""

    type: str = "evergreen"

    # Metadata fields (same as ReferenceNote for consistency)
    created_at: datetime = field(default_factory=datetime.now)
    confidence_score: Optional[float] = None
    sources: List[Dict[str, str]] = field(default_factory=list)
    # Structure: [{"url": str, "title": str (optional), "accessed_date": str (optional), "note": str (optional)}]

    def _get_metadata(self) -> dict:
        return {
            'title': self.title,
            'type': self.type,
            'created': self.created_at.isoformat(),
            'confidence_score': self.confidence_score,
            'sources': self.sources
        }

    def set_confidence_score(self, score: float):
        """
        Set confidence score with validation.

        Args:
            score: Confidence score (0.0-1.0)

        Raises:
            ValueError: If score is invalid
        """
        if not isinstance(score, (int, float)):
            raise ValueError(f"Confidence score must be numeric, got {type(score).__name__}")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {score}")

        self.confidence_score = score


# ================================================================
# REVIEW - Child class
# ================================================================
@dataclass
class ReviewNote(Note):
    """Represents a learning note stored as a markdown file."""

    review_mode: Literal['spaced', 'scheduled']
    schedule_pattern: Optional[str]

    # Review metadata
    created_at: datetime
    last_reviewed: Optional[datetime]
    next_review: datetime
    interval_days: int
    ease_factor: float
    review_count: int

    type: str = "review"

    question_performance: Dict[str, float] = field(default_factory=dict)
    priority_questions: List[str] = field(default_factory=list)
    last_session_summary: Dict[str, Any] = field(default_factory=dict)
    learned_content_count: int = 0

    priority_requests: List[Dict[str, Any]] = field(default_factory=list)
    # Structure: [{"topic": str, "reason": str, "requested_at": str, "session_id": str, "addressed_count": int, "active": bool}]

    confidence_score: Optional[float] = None
    sources: List[Dict[str, str]] = field(default_factory=list)
    # Structure: [{"url": str, "title": str (optional), "accessed_date": str (optional), "note": str (optional)}]

    def _get_metadata(self) -> dict:
        return {
            'title': self.title,
            'type': self.type,
            'created': self.created_at.isoformat(),
            'review_mode': self.review_mode,
            'next_review': self.next_review.isoformat(),
            'interval_days': self.interval_days,
            'ease_factor': self.ease_factor,
            'review_count': self.review_count,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'schedule_pattern': self.schedule_pattern,
            'question_performance': self.question_performance,
            'priority_questions': self.priority_questions,
            'last_session_summary': self.last_session_summary,
            'learned_content_count': self.learned_content_count,
            'priority_requests': self.priority_requests,
            'confidence_score': self.confidence_score,
            'sources': self.sources
        }

    def format_full(self) -> str:
        """Format note with all details and full content."""
        lines = [
            f"# {self.title}",
            "",
            f"**File**: {self.filename}",
            f"**Mode**: {self.review_mode}",
            f"**Created**: {self.created_at.strftime('%Y-%m-%d')}",
            f"**Last reviewed**: {self.last_reviewed.strftime('%Y-%m-%d') if self.last_reviewed else 'Never'}",
            f"**Next review**: {self.next_review.strftime('%Y-%m-%d')}",
            f"**Interval**: {self.interval_days} days",
            f"**Ease factor**: {self.ease_factor:.2f}",
            f"**Review count**: {self.review_count}",
            "",
            "---",
            "",
            self.body
        ]

        return "\n".join(lines)

    def days_until_review(self) -> int:
        """Calculate days until next review."""
        delta = self.next_review.replace(hour=0, minute=0, second=0, microsecond=0) - \
                datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return delta.days

    def get_question_score(self, question_hash: str) -> Optional[float]:
        """
        Get the average score for a specific question.

        Args:
            question_hash: Hash of the question

        Returns:
            Average score (0.0-1.0) or None if never asked
        """
        return self.question_performance.get(question_hash)

    def update_question_score(self, question_hash: str, score: float):
        """
        Update question performance using exponential moving average.

        Args:
            question_hash: Hash of the question
            score: New score (0.0-1.0)

        Raises:
            ValueError: If score is invalid
        """
        if not isinstance(score, (int, float)):
            raise ValueError(f"Score must be numeric, got {type(score).__name__}")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {score}")

        if question_hash in self.question_performance:
            # Exponential moving average
            previous_avg = self.question_performance[question_hash]
            self.question_performance[question_hash] = (
                EMA_NEW_WEIGHT * score + EMA_OLD_WEIGHT * previous_avg
            )
        else:
            # First time seeing this question
            self.question_performance[question_hash] = score

    def set_confidence_score(self, score: float):
        """
        Set confidence score with validation.

        Args:
            score: Confidence score (0.0-1.0)

        Raises:
            ValueError: If score is invalid
        """
        if not isinstance(score, (int, float)):
            raise ValueError(f"Confidence score must be numeric, got {type(score).__name__}")
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {score}")

        self.confidence_score = score


# ================================================================
# DRILL - Code drill flashcard
# ================================================================
@dataclass
class DrillNote(Note):
    """Code drill flashcard with ladder-based spaced repetition and three review modes."""

    language: str
    why_captured: str
    created_at: datetime
    last_reviewed: Optional[datetime]
    next_review: datetime
    ladder_step: int
    review_count: int
    fail_streak: int
    needs_rewrite: bool
    variants_status: Literal['pending', 'ready', 'failed']

    type: str = "drill"
    review_mode: str = "ladder"
    tags: List[str] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    buddy_variants: List[Dict[str, Any]] = field(default_factory=list)
    reverse_variants: List[Dict[str, Any]] = field(default_factory=list)

    def _get_metadata(self) -> dict:
        return {
            'title': self.title,
            'type': self.type,
            'language': self.language,
            'tags': self.tags,
            'why_captured': self.why_captured,
            'sources': self.sources,
            'created': self.created_at.isoformat(),
            'review_mode': self.review_mode,
            'ladder_step': self.ladder_step,
            'next_review': self.next_review.isoformat(),
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'review_count': self.review_count,
            'fail_streak': self.fail_streak,
            'needs_rewrite': self.needs_rewrite,
            'variants_status': self.variants_status,
            'buddy_variants': self.buddy_variants,
            'reverse_variants': self.reverse_variants,
        }

    def days_until_review(self) -> int:
        delta = self.next_review.replace(hour=0, minute=0, second=0, microsecond=0) - \
                datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return delta.days

    def parse_prompt_and_answer(self) -> tuple[str, str]:
        """Extract prompt and model answer from the markdown body.

        Body format:
            ## Prompt
            <text>

            ## Model Answer
            ```<language>
            <code>
            ```
        """
        return DrillNote.parse_body(self.body)

    @staticmethod
    def parse_body(body: str) -> tuple[str, str]:
        """Parse a drill body into (prompt, model_answer)."""
        prompt_match = re.search(
            r'^##\s+Prompt\s*\n(.*?)(?=^##\s+Model Answer|\Z)',
            body, re.MULTILINE | re.DOTALL
        )
        answer_match = re.search(
            r'^##\s+Model Answer\s*\n(.*?)\Z',
            body, re.MULTILINE | re.DOTALL
        )
        prompt = prompt_match.group(1).strip() if prompt_match else ""
        raw_answer = answer_match.group(1).strip() if answer_match else ""
        fence = re.match(r'^```[^\n]*\n(.*?)\n```\s*$', raw_answer, re.DOTALL)
        answer = fence.group(1) if fence else raw_answer
        return prompt, answer

    @staticmethod
    def build_body(prompt: str, model_answer: str, language: str) -> str:
        """Render the markdown body from structured parts."""
        return (
            f"## Prompt\n\n{prompt.strip()}\n\n"
            f"## Model Answer\n\n```{language}\n{model_answer.rstrip()}\n```\n"
        )


# ================================================================
# TASK - Task management
# ================================================================
@dataclass
class Task:
    """Task with YAML frontmatter and markdown body."""

    # Core fields
    id: str  # e.g., "2026-02-03-call-dan"
    title: str
    description: str  # Markdown body

    # Categorization
    categories: List[str]  # [people, idea, project, admin]
    workspace: str  # work | personal | contract
    project: Optional[str]  # Link to active-context project

    # Scheduling
    due: datetime
    status: str  # pending | in_progress | completed
    dependencies: List[str] = field(default_factory=list)  # Task IDs that block this task

    # Metadata
    created: datetime = field(default_factory=datetime.now)
    updated: datetime = field(default_factory=datetime.now)
    completed: Optional[datetime] = None

    # Auto-categorization
    confidence: Dict[str, float] = field(default_factory=dict)  # {workspace: 0.85, project: 0.9, ...}
    reasoning: Optional[str] = None  # Why LLM chose these categories

    # Priority link
    priority_id: Optional[str] = None  # FK to priorities table

    # Daily pin (max 3 at a time)
    pinned: bool = False

    filename: str = ""  # Generated from id

    @classmethod
    def from_markdown_file(cls, filepath: Path) -> 'Task':
        """
        Load task from markdown file with YAML frontmatter.

        Args:
            filepath: Path to the markdown file

        Returns:
            Task instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        now = datetime.now()

        return Task(
            id=str(post.get('id', filepath.stem)),
            title=str(post.get('title', '')),
            description=str(post.content),
            categories=parse_categories(post.get('categories')),
            workspace=parse_workspace(post.get('workspace')),
            project=str(post['project']) if post.get('project') else None,
            due=parse_datetime(post.get('due'), now),
            status=str(post.get('status', 'pending')),
            dependencies=parse_categories(post.get('dependencies')),
            created=parse_datetime(post.get('created'), now),
            updated=parse_datetime(post.get('updated'), now),
            completed=parse_datetime(post['completed'], now) if post.get('completed') else None,
            confidence=parse_confidence(post.get('confidence')),
            reasoning=str(post['reasoning']) if post.get('reasoning') else None,
            filename=filepath.name
        )

    def to_markdown_file(self) -> str:
        """
        Serialize task to markdown with YAML frontmatter.

        Returns:
            String containing the complete markdown file
        """
        metadata = {
            'id': self.id,
            'title': self.title,
            'categories': self.categories,
            'workspace': self.workspace,
            'project': self.project,
            'due': self.due.isoformat(),
            'status': self.status,
            'dependencies': self.dependencies,
            'created': self.created.isoformat(),
            'updated': self.updated.isoformat(),
            'completed': self.completed.isoformat() if self.completed else None,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }

        post = frontmatter.Post(self.description, **metadata)
        return frontmatter.dumps(post)

    @staticmethod
    def create_id(title: str, due: datetime) -> str:
        """
        Generate task ID: YYYY-MM-DD-slug.

        Args:
            title: Task title
            due: Due date

        Returns:
            Task ID string
        """
        # Format date prefix
        date_prefix = due.strftime('%Y-%m-%d')

        # Create slug from title
        safe_title = ''.join(c if c.isalnum() or c.isspace() else '' for c in title)
        slug = '-'.join(safe_title.lower().split())

        # Limit slug length
        if len(slug) > 40:
            slug = slug[:40]

        return f"{date_prefix}-{slug}"

    @staticmethod
    def create_filename(task_id: str) -> str:
        """
        Create filename from task ID.

        Args:
            task_id: Task ID

        Returns:
            Filename with .md extension
        """
        return f"{task_id}.md"


# ================================================================
# DAILY LOG - Daily workflow
# ================================================================
@dataclass
class DailyLog:
    """Daily log with tasks and reflection."""

    date: datetime  # 2026-02-02
    tasks_due_today: List[str] = field(default_factory=list)  # Task IDs
    tasks_overdue: List[str] = field(default_factory=list)  # Task IDs
    tasks_this_week: List[str] = field(default_factory=list)  # Task IDs
    priorities: List[str] = field(default_factory=list)  # Ordered task IDs

    # Evening reflection
    completed: List[Dict[str, Any]] = field(default_factory=list)  # [{task_id, notes}, ...]
    incomplete: List[Dict[str, Any]] = field(default_factory=list)  # [{task_id, reason, rollover}, ...]
    new_tasks: List[str] = field(default_factory=list)  # Task IDs created during reflection
    reflection_notes: Optional[str] = None  # General notes about the day

    @classmethod
    def from_markdown_file(cls, filepath: Path) -> 'DailyLog':
        """
        Parse daily log markdown.

        Args:
            filepath: Path to the markdown file

        Returns:
            DailyLog instance

        Note: This is a simplified parser that extracts task IDs from markdown.
        The daily log format is human-readable and may not be strictly parseable.
        """
        # Extract date from filename (YYYY-MM-DD.md)
        date_str = filepath.stem
        date = datetime.fromisoformat(date_str)

        # For now, return a basic DailyLog
        # The daily log is primarily generated, not parsed
        return DailyLog(date=date)

    def to_markdown_file(self) -> str:
        """
        Generate daily log markdown.

        Returns:
            String containing the complete markdown file
        """
        lines = [
            f"# Daily Log - {self.date.strftime('%A, %Y-%m-%d')}",
            "",
            "## Today's Tasks",
            ""
        ]

        if self.tasks_overdue:
            lines.append("### Overdue ({})".format(len(self.tasks_overdue)))
            for task_id in self.tasks_overdue:
                lines.append(f"- [ ] 🔴 {task_id}")
            lines.append("")

        if self.tasks_due_today:
            lines.append("### Due Today ({})".format(len(self.tasks_due_today)))
            for task_id in self.tasks_due_today:
                lines.append(f"- [ ] {task_id}")
            lines.append("")

        if self.tasks_this_week:
            lines.append("### This Week ({})".format(len(self.tasks_this_week)))
            for task_id in self.tasks_this_week:
                lines.append(f"- [ ] {task_id}")
            lines.append("")

        if self.priorities:
            lines.append("## Priorities")
            for i, task_id in enumerate(self.priorities, 1):
                lines.append(f"{i}. {task_id}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## Evening Reflection",
            "",
            "### Completed",
            ""
        ])

        for item in self.completed:
            task_id = item.get('task_id', '')
            notes = item.get('notes', '')
            lines.append(f"✓ **{task_id}**")
            if notes:
                lines.append(f"  - Notes: {notes}")
            lines.append("")

        lines.extend([
            "### Incomplete",
            ""
        ])

        for item in self.incomplete:
            task_id = item.get('task_id', '')
            reason = item.get('reason', '')
            rollover = item.get('rollover', False)
            lines.append(f"✗ **{task_id}**" + (" → Rolling to tomorrow" if rollover else ""))
            if reason:
                lines.append(f"  - Reason: {reason}")
            lines.append("")

        if self.new_tasks:
            lines.extend([
                "### New Tasks Created",
                ""
            ])
            for task_id in self.new_tasks:
                lines.append(f"- {task_id}")
            lines.append("")

        if self.reflection_notes:
            lines.extend([
                "### Notes",
                self.reflection_notes,
                ""
            ])

        return "\n".join(lines)
