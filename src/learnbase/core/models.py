"""Data models for LearnBase."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Literal
from pathlib import Path
import frontmatter


# Exponential Moving Average weights for question performance tracking
# These control how quickly the performance metric adapts to new scores
EMA_NEW_WEIGHT = 0.7  # Weight given to the new score (70%)
EMA_OLD_WEIGHT = 0.3  # Weight given to the previous average (30%)
# Note: Higher new weight = faster adaptation to recent performance
# Lower new weight = more stability, slower to reflect improvement


@dataclass
class Note:
    """Represents a learning note stored as a markdown file."""

    filename: str  # e.g., "python-gil.md"
    title: str
    body: str  # Markdown content
    review_mode: Literal['spaced', 'scheduled']
    schedule_pattern: Optional[str]

    # Review metadata
    created_at: datetime
    last_reviewed: Optional[datetime]
    next_review: datetime
    interval_days: int
    ease_factor: float
    review_count: int

    # Interactive review metadata
    question_performance: Dict[str, float] = field(default_factory=dict)  # question_hash -> avg score
    priority_questions: List[str] = field(default_factory=list)  # question hashes sorted worst to best
    last_session_summary: Dict[str, Any] = field(default_factory=dict)  # last session details
    learned_content_count: int = 0  # track note expansions

    # Explicit priority requests from user (topic-level)
    priority_requests: List[Dict[str, Any]] = field(default_factory=list)  # user-requested focus areas
    # Structure: [{"topic": str, "reason": str, "requested_at": str, "session_id": str, "addressed_count": int, "active": bool}]

    @classmethod
    def from_markdown_file(cls, filepath: Path) -> 'Note':
        """
        Create a Note from a markdown file with YAML frontmatter.

        Args:
            filepath: Path to the markdown file

        Returns:
            Note instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Parse dates
        created_at = datetime.fromisoformat(post.get('created', datetime.now().isoformat()))
        last_reviewed = None
        if post.get('last_reviewed'):
            last_reviewed = datetime.fromisoformat(post['last_reviewed'])
        next_review = datetime.fromisoformat(post.get('next_review', datetime.now().isoformat()))

        return cls(
            filename=filepath.name,
            title=post.get('title', filepath.stem.replace('-', ' ').title()),
            body=post.content,
            review_mode=post.get('review_mode', 'spaced'),
            schedule_pattern=post.get('schedule_pattern'),
            created_at=created_at,
            last_reviewed=last_reviewed,
            next_review=next_review,
            interval_days=post.get('interval_days', 1),
            ease_factor=post.get('ease_factor', 2.5),
            review_count=post.get('review_count', 0),
            question_performance=post.get('question_performance', {}),
            priority_questions=post.get('priority_questions', []),
            last_session_summary=post.get('last_session_summary', {}),
            learned_content_count=post.get('learned_content_count', 0),
            priority_requests=post.get('priority_requests', [])
        )

    def to_markdown_file(self) -> str:
        """
        Convert Note to markdown file content with YAML frontmatter.

        Returns:
            String containing the complete markdown file
        """
        metadata = {
            'title': self.title,
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
            'priority_requests': self.priority_requests
        }

        post = frontmatter.Post(self.body, **metadata)
        return frontmatter.dumps(post)

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
