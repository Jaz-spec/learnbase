"""Note manager for markdown-based learning notes."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Any, Tuple, Literal, Dict
import re
import logging
import json

from .models import Note
from .spaced_rep import calculate_next_review, calculate_scheduled_review

logger = logging.getLogger(__name__)


class NoteManager:
    """Manages markdown-based learning notes and README index."""

    def __init__(self, notes_dir: Optional[Path] = None):
        """
        Initialize NoteManager.

        Args:
            notes_dir: Directory to store notes (default: ~/.learnbase/notes)
        """
        if notes_dir is None:
            notes_dir = Path.home() / ".learnbase" / "notes"

        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.readme_path = self.notes_dir / "README.md"

        # Create history directory for session tracking
        self.history_dir = Path.home() / ".learnbase" / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # Initialize README if it doesn't exist
        if not self.readme_path.exists():
            self._create_readme()

    def _validate_filename(self, filename: str) -> None:
        """
        Validate filename to prevent path traversal and ensure safety.

        Args:
            filename: Note filename to validate

        Raises:
            ValueError: If filename is invalid or unsafe
        """
        if not filename:
            raise ValueError("Filename cannot be empty")

        # Check for path traversal (directory separators)
        if Path(filename).name != filename:
            raise ValueError(
                f"Filename must not contain directory separators: '{filename}'"
            )

        # Check for hidden files (security best practice)
        if filename.startswith('.'):
            raise ValueError(f"Filename must not start with dot: '{filename}'")

        # Check for .md extension
        if not filename.endswith('.md'):
            raise ValueError(f"Filename must have .md extension: '{filename}'")

        # Check for valid characters (alphanumeric, hyphen, underscore, dot only)
        base_name = filename[:-3]  # Remove .md extension
        if not all(c.isalnum() or c in '-_' for c in base_name):
            raise ValueError(
                f"Filename contains invalid characters: '{filename}'. "
                f"Only alphanumeric, hyphens, and underscores allowed."
            )

        logger.debug(f"Validated filename: {filename}")

    def _save_note(self, note: Note, filepath: Path) -> None:
        """
        Save note to file with proper error handling.

        Args:
            note: Note instance to save
            filepath: Full path where note should be saved

        Raises:
            IOError: If file cannot be written
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(note.to_markdown_file())
            logger.debug(f"Saved note to {filepath.name}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to save note {filepath.name}: {e}")
            raise IOError(f"Failed to save note {filepath.name}: {e}") from e

    def _get_note_or_raise(self, filename: str) -> Note:
        """
        Get note or raise ValueError if not found.

        Args:
            filename: Note filename

        Returns:
            Note instance

        Raises:
            ValueError: If note not found
        """
        note = self.get_note(filename)
        if not note:
            raise ValueError(f"Note '{filename}' not found")
        logger.debug(f"Retrieved note: {filename}")
        return note

    def _create_unique_filename(self, base_filename: str) -> tuple[str, Path]:
        """
        Create unique filename atomically to prevent race conditions.

        Uses os.O_CREAT | os.O_EXCL for atomic file creation.

        Args:
            base_filename: Base filename to start with (e.g., "python-gil.md")

        Returns:
            Tuple of (final_filename, full_filepath)

        Raises:
            RuntimeError: If unable to create unique filename after 1000 attempts
        """
        import os
        base = base_filename.replace('.md', '')
        filename = base_filename
        filepath = self.notes_dir / filename
        counter = 1

        while counter < 1000:
            try:
                # Atomic file creation - fails if file exists
                fd = os.open(str(filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.close(fd)
                logger.debug(f"Created unique filename: {filename}")
                return filename, filepath
            except FileExistsError:
                filename = f"{base}-{counter}.md"
                filepath = self.notes_dir / filename
                counter += 1

        raise RuntimeError(f"Failed to create unique filename after 1000 attempts")

    def create_note(
        self,
        title: str,
        body: str,
        review_mode: Literal['spaced', 'scheduled'] = 'spaced',
        schedule_pattern: Optional[str] = None
    ) -> str:
        """
        Create a new note.

        Args:
            title: Note title
            body: Markdown content
            review_mode: 'spaced' or 'scheduled'
            schedule_pattern: Schedule pattern if using scheduled mode

        Returns:
            Filename of created note
        """
        # Validate title
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        if len(title) > 200:
            raise ValueError("Title cannot exceed 200 characters")

        # Validate body
        if not body or not body.strip():
            raise ValueError("Body cannot be empty")

        # Validate review_mode
        if review_mode not in ('spaced', 'scheduled'):
            raise ValueError(f"Invalid review_mode: '{review_mode}'. Must be 'spaced' or 'scheduled'")

        # Validate schedule_pattern for scheduled mode
        if review_mode == 'scheduled':
            if not schedule_pattern:
                raise ValueError("Schedule pattern required for scheduled mode")
            # Test parsing
            try:
                from .spaced_rep import parse_schedule_pattern
                intervals = parse_schedule_pattern(schedule_pattern)
                if not intervals:
                    raise ValueError("Schedule pattern must produce at least one interval")
            except Exception as e:
                raise ValueError(f"Invalid schedule pattern '{schedule_pattern}': {e}")

        logger.debug(f"Creating note: title='{title[:50]}...', review_mode={review_mode}")
        filename = Note.create_filename(title)
        filepath = self.notes_dir / filename

        # Atomically create unique filename to prevent race conditions
        if filepath.exists():
            filename, filepath = self._create_unique_filename(filename)
        else:
            import os
            try:
                # Atomic file creation - fails if file exists
                fd = os.open(str(filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.close(fd)
            except FileExistsError:
                # Race condition occurred, fall back to unique filename helper
                filename, filepath = self._create_unique_filename(filename)

        now = datetime.now()

        note = Note(
            filename=filename,
            title=title,
            body=body,
            review_mode=review_mode,
            schedule_pattern=schedule_pattern,
            created_at=now,
            last_reviewed=None,
            next_review=now,  # Due immediately for first review
            interval_days=1,
            ease_factor=2.5,
            review_count=0
        )

        # Write to file
        self._save_note(note, filepath)

        # Update README
        self.update_readme_index()

        logger.info(f"Created note: {filename}")
        return filename

    def get_note(self, filename: str) -> Optional[Note]:
        """
        Get a specific note by filename.

        Args:
            filename: Note filename (e.g., "python-gil.md")

        Returns:
            Note instance or None if not found
        """
        self._validate_filename(filename)
        filepath = self.notes_dir / filename

        if not filepath.exists():
            logger.warning(f"Note file not found: {filename}")
            return None

        try:
            note = Note.from_markdown_file(filepath)
            logger.debug(f"Successfully loaded note: {filename}")
            return note
        except (IOError, OSError) as e:
            logger.error(f"I/O error loading note {filename}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid note format in {filename}: {e}")
            return None
        except Exception as e:
            logger.critical(f"Unexpected error loading note {filename}: {e}", exc_info=True)
            return None

    def get_all_notes(self) -> List[Note]:
        """
        Get all notes.

        Returns:
            List of Note instances
        """
        notes = []

        for filepath in self.notes_dir.glob("*.md"):
            if filepath.name == "README.md":
                continue

            try:
                note = Note.from_markdown_file(filepath)
                notes.append(note)
                logger.debug(f"Loaded note: {filepath.name}")
            except (IOError, OSError) as e:
                logger.error(f"I/O error loading note {filepath.name}: {e}")
                continue
            except ValueError as e:
                logger.error(f"Invalid note format in {filepath.name}: {e}")
                continue
            except Exception as e:
                logger.critical(f"Unexpected error loading note {filepath.name}: {e}", exc_info=True)
                continue

        # Sort by next_review date
        notes.sort(key=lambda n: n.next_review)

        return notes

    def get_due_notes(
        self,
        limit: Optional[int] = None,
        review_mode: Optional[Literal['spaced', 'scheduled']] = None,
        require_verified: bool = False
    ) -> List[Note]:
        """
        Get notes that are due for review.

        Args:
            limit: Maximum number of notes to return
            review_mode: Filter by review mode ('spaced' or 'scheduled')
            require_verified: Only include verified notes (with sources and confidence >= 0.6)

        Returns:
            List of Note instances due for review
        """
        all_notes = self.get_all_notes()
        now = datetime.now()

        # Filter due notes
        due_notes = [n for n in all_notes if n.next_review <= now]

        # Filter by review mode if specified
        if review_mode:
            due_notes = [n for n in due_notes if n.review_mode == review_mode]

        # Filter by verification status if required
        if require_verified:
            due_notes = [
                n for n in due_notes
                if n.sources and (n.confidence_score is None or n.confidence_score >= 0.6)
            ]

        # Apply limit
        if limit:
            due_notes = due_notes[:limit]

        return due_notes

    def get_notes_needing_verification(self, limit: Optional[int] = None) -> List[Note]:
        """
        Get notes that need verification (have no sources).

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of Note instances with empty sources, sorted by next_review date
        """
        all_notes = self.get_all_notes()

        # Filter notes with no sources
        unverified_notes = [n for n in all_notes if not n.sources]

        # Already sorted by next_review in get_all_notes()

        # Apply limit
        if limit:
            unverified_notes = unverified_notes[:limit]

        return unverified_notes

    def get_notes_with_low_confidence(
        self,
        threshold: float = 0.6,
        limit: Optional[int] = None
    ) -> List[Note]:
        """
        Get notes with confidence score below threshold.

        Args:
            threshold: Confidence threshold (0.0-1.0), default 0.6
            limit: Maximum number of notes to return

        Returns:
            List of Note instances with low confidence, sorted by confidence_score (lowest first)
        """
        if not isinstance(threshold, (int, float)):
            raise ValueError(f"Threshold must be numeric, got {type(threshold).__name__}")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        all_notes = self.get_all_notes()

        # Filter notes with confidence score below threshold
        # Exclude notes with None confidence_score
        low_confidence_notes = [
            n for n in all_notes
            if n.confidence_score is not None and n.confidence_score < threshold
        ]

        # Sort by confidence score (lowest first)
        low_confidence_notes.sort(key=lambda n: n.confidence_score)

        # Apply limit
        if limit:
            low_confidence_notes = low_confidence_notes[:limit]

        return low_confidence_notes

    def update_note_review(self, filename: str, rating: int):
        """
        Update note after review.

        Args:
            filename: Note filename
            rating: User rating (1-4)
        """
        self._validate_filename(filename)

        # Validate rating
        if not isinstance(rating, int):
            raise ValueError(f"Rating must be an integer, got {type(rating).__name__}")
        if not 1 <= rating <= 4:
            raise ValueError(f"Rating must be between 1 and 4, got {rating}")

        logger.debug(f"Updating review: {filename}, rating={rating}")

        note = self._get_note_or_raise(filename)

        # Calculate next review based on mode
        if note.review_mode == 'spaced':
            new_interval, new_ease, next_review = calculate_next_review(
                rating,
                note.interval_days,
                note.ease_factor,
                note.review_count
            )
        else:  # scheduled mode
            new_interval, next_review = calculate_scheduled_review(
                rating,
                note.schedule_pattern or "1d,1w,2w,1m,3m,6m",
                note.review_count
            )
            new_ease = note.ease_factor  # unchanged in scheduled mode

        # Update note
        note.last_reviewed = datetime.now()
        note.next_review = next_review
        note.interval_days = new_interval
        note.ease_factor = new_ease
        note.review_count += 1

        # Write back to file
        filepath = self.notes_dir / filename
        self._save_note(note, filepath)

        # Update README
        self.update_readme_index()

        logger.info(f"Updated review for {filename}: rating={rating}, next_review={next_review}")

    def update_note_content(self, filename: str, title: str, body: str):
        """
        Update note content (edit operation).

        Args:
            filename: Note filename
            title: New title
            body: New markdown content
        """
        self._validate_filename(filename)

        # Validate title
        if not title or not title.strip():
            raise ValueError("Title cannot be empty")
        if len(title) > 200:
            raise ValueError("Title cannot exceed 200 characters")

        # Validate body
        if not body or not body.strip():
            raise ValueError("Body cannot be empty")

        logger.debug(f"Updating note content: {filename}")

        note = self._get_note_or_raise(filename)

        note.title = title
        note.body = body

        # Write back to file
        filepath = self.notes_dir / filename
        self._save_note(note, filepath)

        # Update README
        self.update_readme_index()

        logger.info(f"Updated content for {filename}")

    def delete_note(self, filename: str) -> bool:
        """
        Delete a note.

        Args:
            filename: Note filename

        Returns:
            True if deleted, False if not found
        """
        self._validate_filename(filename)
        filepath = self.notes_dir / filename

        if not filepath.exists():
            logger.warning(f"Cannot delete note {filename}: not found")
            return False

        filepath.unlink()

        # Update README
        self.update_readme_index()

        logger.info(f"Deleted note: {filename}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get learning statistics.

        Returns:
            Dictionary with statistics
        """
        all_notes = self.get_all_notes()
        now = datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        week_end = now + timedelta(days=7)

        # Count due notes
        due_today = [n for n in all_notes if n.next_review <= today_end]
        due_week = [n for n in all_notes if today_end < n.next_review <= week_end]

        # Count reviewed today (using date comparison)
        today_date = now.date()
        reviewed_today = [
            n for n in all_notes
            if n.last_reviewed and n.last_reviewed.date() == today_date
        ]

        # Average ease factor
        reviewed_notes = [n for n in all_notes if n.review_count > 0]
        avg_ease = sum(n.ease_factor for n in reviewed_notes) / len(reviewed_notes) if reviewed_notes else 2.5

        return {
            "total_notes": len(all_notes),
            "reviewed_today": len(reviewed_today),
            "due_today": len(due_today),
            "due_this_week": len(due_week),
            "average_ease": avg_ease,
            "spaced_notes": len([n for n in all_notes if n.review_mode == 'spaced']),
            "scheduled_notes": len([n for n in all_notes if n.review_mode == 'scheduled'])
        }

    def update_readme_index(self):
        """Update README.md with current notes index and statistics."""
        notes = self.get_all_notes()
        stats = self.get_stats()

        # Build README content
        lines = [
            "# LearnBase Learning Notes",
            "",
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Statistics",
            f"- Total notes: {stats['total_notes']}",
            f"- Due today: {stats['due_today']}",
            f"- Reviewed today: {stats['reviewed_today']}",
            f"- Spaced repetition: {stats['spaced_notes']} notes",
            f"- Scheduled: {stats['scheduled_notes']} notes",
            f"- Average ease factor: {stats['average_ease']:.2f}",
            "",
            "## Notes Registry",
            "",
            "| File | Title | Mode | Next Review | Reviews | Ease |",
            "|------|-------|------|-------------|---------|------|"
        ]

        # Add notes to table
        for note in notes:
            next_review_str = note.next_review.strftime('%Y-%m-%d')
            lines.append(
                f"| {note.filename} | {note.title[:40]} | {note.review_mode} | "
                f"{next_review_str} | {note.review_count} | {note.ease_factor:.2f} |"
            )

        lines.extend(["", "## Recent Updates", ""])

        # Add recent updates (last 10 reviewed notes)
        reviewed_notes = [n for n in notes if n.last_reviewed]
        reviewed_notes.sort(key=lambda n: n.last_reviewed, reverse=True)

        for note in reviewed_notes[:10]:
            date_str = note.last_reviewed.strftime('%Y-%m-%d')
            lines.append(f"- {date_str}: Reviewed {note.filename} ({note.title})")

        # Write README
        with open(self.readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _get_history_path(self, filename: str) -> Path:
        """
        Get the path to the history file for a note.

        Args:
            filename: Note filename (e.g., "python-gil.md")

        Returns:
            Path to history JSON file
        """
        self._validate_filename(filename)
        # Remove .md extension and add .json
        base_name = filename.replace('.md', '')
        return self.history_dir / f"{base_name}.json"

    def load_history(self, filename: str) -> dict:
        """
        Load session history for a note.

        Args:
            filename: Note filename

        Returns:
            History dictionary with sessions list
        """
        self._validate_filename(filename)
        history_path = self._get_history_path(filename)

        if not history_path.exists():
            logger.debug(f"No history file found for {filename}")
            return {"note_filename": filename, "sessions": []}

        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            logger.debug(f"Loaded history for {filename}: {len(history.get('sessions', []))} sessions")
            return history
        except FileNotFoundError:
            logger.debug(f"No history file found for {filename}")
            return {"note_filename": filename, "sessions": []}
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted history file for {filename}: {e}")
            return {"note_filename": filename, "sessions": []}
        except (IOError, OSError) as e:
            logger.error(f"I/O error loading history for {filename}: {e}")
            return {"note_filename": filename, "sessions": []}

    def save_session_history(self, filename: str, session: dict):
        """
        Save a session to the note's history file.

        Args:
            filename: Note filename
            session: Session dictionary to save
        """
        self._validate_filename(filename)
        history = self.load_history(filename)
        history["sessions"].append(session)

        history_path = self._get_history_path(filename)

        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved session history for {filename}")
        except (IOError, OSError) as e:
            logger.error(f"Failed to save history for {filename}: {e}")
            raise

    def bulk_update_question_performance(
        self,
        filename: str,
        question_scores: List[Tuple[str, float]]
    ):
        """
        Update multiple question performances in a single file write.
        More efficient than calling update_question_performance repeatedly.

        Args:
            filename: Note filename
            question_scores: List of (question_hash, score) tuples
        """
        self._validate_filename(filename)

        # Validate question_scores list
        if not question_scores:
            raise ValueError("Question scores list cannot be empty")

        if not isinstance(question_scores, list):
            raise ValueError("Question scores must be a list of (hash, score) tuples")

        # Validate each tuple
        for i, item in enumerate(question_scores):
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError(f"Item {i} must be a (question_hash, score) tuple")

            question_hash, score = item

            if not question_hash or not isinstance(question_hash, str):
                raise ValueError(f"Question hash at index {i} must be a non-empty string")

            if not isinstance(score, (int, float)):
                raise ValueError(f"Score at index {i} must be numeric, got {type(score).__name__}")

            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Score at index {i} must be between 0.0 and 1.0, got {score}")

        logger.debug(f"Bulk updating {len(question_scores)} question performances for {filename}")

        note = self._get_note_or_raise(filename)

        # Apply EMA algorithm to all questions
        for question_hash, score in question_scores:
            note.update_question_score(question_hash, score)

        # Single write operation
        filepath = self.notes_dir / filename
        self._save_note(note, filepath)

        logger.debug(f"Bulk updated {len(question_scores)} question performances for {filename}")

    def update_priority_requests(
        self,
        filename: str,
        new_requests: List[dict],
        addressed_topics: List[str],
        session_id: str
    ) -> None:
        """
        Update priority requests based on session activity.

        Args:
            filename: Note filename
            new_requests: List of {topic, reason} dicts for new priorities
            addressed_topics: List of topic strings that were covered
            session_id: Current session ID
        """
        self._validate_filename(filename)
        note = self._get_note_or_raise(filename)

        ADDRESSED_THRESHOLD = 2

        # Process new priority requests
        for req in new_requests:
            topic = req.get("topic")
            reason = req.get("reason", "User requested focus on this area")

            if not topic:
                logger.warning(f"Skipping priority request with missing topic: {req}")
                continue

            # Check if topic already has an active request
            found = False
            for existing in note.priority_requests:
                if existing["topic"].lower() == topic.lower() and existing["active"]:
                    # Reactivate/update existing request
                    existing["reason"] = reason
                    existing["requested_at"] = datetime.now().isoformat()
                    existing["session_id"] = session_id
                    found = True
                    logger.debug(f"Updated existing priority request for '{topic}'")
                    break

            if not found:
                # Add new request
                note.priority_requests.append({
                    "topic": topic,
                    "reason": reason,
                    "requested_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "addressed_count": 0,
                    "active": True
                })
                logger.debug(f"Added new priority request for '{topic}'")

        # Process addressed priorities
        for topic in addressed_topics:
            for existing in note.priority_requests:
                if existing["topic"].lower() == topic.lower() and existing["active"]:
                    existing["addressed_count"] += 1

                    if existing["addressed_count"] >= ADDRESSED_THRESHOLD:
                        existing["active"] = False
                        logger.info(f"Deactivated priority '{topic}' after {existing['addressed_count']} sessions")
                    else:
                        logger.debug(f"Incremented priority '{topic}' to {existing['addressed_count']}/{ADDRESSED_THRESHOLD}")

                    break

        # Save updated note
        filepath = self.notes_dir / filename
        self._save_note(note, filepath)
        logger.info(f"Updated priorities for {filename}: {len(new_requests)} new, {len(addressed_topics)} addressed")

    def _create_readme(self):
        """Create initial README.md file."""
        content = """# LearnBase Learning Notes

This directory contains your learning notes managed by LearnBase.

Each note is a markdown file with YAML frontmatter containing review metadata.

## Getting Started

Use the MCP server to interact with your notes conversationally, or use the CLI:

```bash
learn add "Your Note Title"
learn list
learn show note-filename.md
```

For more information, see the main README in the learnbase repository.
"""
        with open(self.readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
