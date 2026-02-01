"""Data models for LearnBase."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Literal, cast
from pathlib import Path
import frontmatter

from .parsers import (
    parse_datetime,
    parse_review,
    parse_int,
    parse_float,
    parse_optional_float,
    parse_list,
    parse_dict
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

        if note_type == 'reference':
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
