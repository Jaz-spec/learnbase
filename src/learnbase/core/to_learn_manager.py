"""Manager for to-learn topics stored in a single markdown file."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import re
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)


class ToLearnManager:
    """Manages learning topics in a single markdown file with table and sections."""

    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize ToLearnManager.

        Args:
            file_path: Path to to_learn.md file (default: ~/.learnbase/to_learn.md)
        """
        if file_path is None:
            file_path = Path.home() / ".learnbase" / "to_learn.md"

        self.file_path = Path(file_path)
        self.learnbase_dir = self.file_path.parent
        self.learnbase_dir.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.file_path.exists():
            self._create_initial_file()
            logger.info(f"Created initial to_learn.md at {self.file_path}")

    def _create_initial_file(self):
        """Create initial empty to_learn.md file."""
        content = """# Topics to Learn

> Last updated: {timestamp}
> Total topics: 0

## Quick Capture Topics

| Topic | Added | Context |
|-------|-------|---------|

## Detailed Topics

## Archive

### Completed Topics
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(content)


    def _validate_topic_name(self, topic: str) -> None:
        """
        Validate topic name.

        Args:
            topic: Topic name to validate

        Raises:
            ValueError: If topic name is invalid
        """
        if not topic or not topic.strip():
            raise ValueError("Topic name cannot be empty")

        if len(topic) > 200:
            raise ValueError("Topic name cannot exceed 200 characters")

    def _sanitize_topic_for_header(self, topic: str) -> str:
        """
        Sanitize topic name for use in markdown header.

        Args:
            topic: Topic name

        Returns:
            Sanitized topic name safe for markdown headers
        """
        # Remove or replace characters that might break markdown
        sanitized = topic.replace('#', '').replace('[', '').replace(']', '')
        return sanitized.strip()

    def _parse_file(self) -> Dict[str, Any]:
        """
        Parse the to_learn.md file into structured data.

        Returns:
            Dictionary with 'quick' and 'detailed' and 'archived' topics
        """
        if not self.file_path.exists():
            return {"quick": [], "detailed": [], "archived": []}

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError) as e:
            logger.error(f"Failed to read {self.file_path}: {e}")
            raise IOError(f"Failed to read to_learn.md: {e}") from e

        quick_topics = []
        detailed_topics = []
        archived_topics = []

        # Split content by main sections
        sections = re.split(r'\n## ', content)

        for section in sections:
            section_lower = section.lower()

            # Parse Quick Capture Topics table
            if section_lower.startswith('quick capture topics'):
                quick_topics = self._parse_quick_table(section)

            # Parse Detailed Topics
            elif section_lower.startswith('detailed topics'):
                detailed_topics = self._parse_detailed_section(section)

            # Parse Archive
            elif section_lower.startswith('archive'):
                archived_topics = self._parse_archive_section(section)

        return {
            "quick": quick_topics,
            "detailed": detailed_topics,
            "archived": archived_topics
        }

    def _parse_quick_table(self, section: str) -> List[Dict]:
        """Parse the Quick Capture Topics table."""
        topics = []
        lines = section.split('\n')

        # Find table rows (skip header and separator)
        in_table = False
        for line in lines:
            # Match separator line (can have spaces: "| ---" or "|---")
            if line.strip().startswith('|') and '---' in line and all(c in '|- ' for c in line.replace('|', '').strip()):
                in_table = True
                continue

            if in_table and line.strip().startswith('|'):
                # Parse table row
                parts = [p.strip() for p in line.split('|')[1:-1]]  # Skip empty first/last
                if len(parts) >= 3:
                    topics.append({
                        "topic": parts[0],
                        "added": parts[1],
                        "context": parts[2] if len(parts) > 2 else "",
                        "detailed": False,
                        "notes": "",
                        "archived": False
                    })

        return topics

    def _parse_detailed_section(self, section: str) -> List[Dict]:
        """Parse the Detailed Topics section."""
        topics = []

        # Split by ### headers (individual topics)
        topic_sections = re.split(r'\n### ', section)

        for topic_section in topic_sections[1:]:  # Skip first (section header)
            lines = topic_section.split('\n')
            if not lines:
                continue

            topic_name = lines[0].strip()
            added = ""
            context = ""
            notes_lines = []

            # Parse metadata and notes
            for i, line in enumerate(lines[1:], 1):
                if line.startswith('**Added:**'):
                    added = line.replace('**Added:**', '').strip()
                elif line.startswith('**Context:**'):
                    context = line.replace('**Context:**', '').strip()
                elif line.strip() and not line.startswith('**'):
                    # Content lines
                    notes_lines.append(line)

            topics.append({
                "topic": topic_name,
                "added": added,
                "context": context,
                "detailed": True,
                "notes": '\n'.join(notes_lines).strip(),
                "archived": False
            })

        return topics

    def _parse_archive_section(self, section: str) -> List[Dict]:
        """Parse the Archive section."""
        topics = []

        # Similar to detailed topics parsing
        topic_sections = re.split(r'\n### ', section)

        for topic_section in topic_sections[1:]:
            lines = topic_section.split('\n')
            if not lines:
                continue

            topic_name = lines[0].strip()

            # Skip the "Completed Topics" header itself
            if topic_name.lower() == "completed topics":
                continue

            added = ""
            completed = ""
            context = ""
            notes_lines = []

            for line in lines[1:]:
                if line.startswith('**Added:**'):
                    added = line.replace('**Added:**', '').strip()
                elif line.startswith('**Completed:**'):
                    completed = line.replace('**Completed:**', '').strip()
                elif line.startswith('**Context:**'):
                    context = line.replace('**Context:**', '').strip()
                elif line.strip() and not line.startswith('**'):
                    notes_lines.append(line)

            # Only add if we have valid data (added date at minimum)
            if added or topic_name:
                topics.append({
                    "topic": topic_name,
                    "added": added,
                    "completed": completed,
                    "context": context,
                    "detailed": True,
                    "notes": '\n'.join(notes_lines).strip(),
                    "archived": True
                })

        return topics

    def _write_file(self, data: Dict[str, List[Dict]]) -> None:
        """
        Write structured data back to file atomically.

        Args:
            data: Dictionary with 'quick', 'detailed', and 'archived' topics
        """
        # Calculate counts
        all_active_topics = data["quick"] + data["detailed"]
        total = len(all_active_topics)

        # Build content
        lines = [
            "# Topics to Learn",
            "",
            f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> Total topics: {total}",
            "",
            "## Quick Capture Topics",
            "",
            "| Topic | Added | Context |",
            "|-------|-------|---------|"
        ]

        # Add quick topics table rows
        for topic in data["quick"]:
            lines.append(
                f"| {topic['topic']} | {topic['added']} | {topic['context']} |"
            )

        lines.extend(["", "## Detailed Topics", ""])

        # Add detailed topics
        for topic in data["detailed"]:
            sanitized_name = self._sanitize_topic_for_header(topic['topic'])
            lines.append(f"### {sanitized_name}")
            lines.append(f"**Added:** {topic['added']}")
            if topic['context']:
                lines.append(f"**Context:** {topic['context']}")
            lines.append("")
            if topic['notes']:
                lines.append(topic['notes'])
                lines.append("")

        lines.extend(["## Archive", "", "### Completed Topics", ""])

        # Add archived topics
        for topic in data["archived"]:
            sanitized_name = self._sanitize_topic_for_header(topic['topic'])
            lines.append(f"### {sanitized_name}")
            lines.append(f"**Added:** {topic['added']}")
            if topic.get('completed'):
                lines.append(f"**Completed:** {topic['completed']}")
            lines.append(f"**Context:** {topic['context']}")
            lines.append("")
            if topic['notes']:
                lines.append(topic['notes'])
                lines.append("")

        content = '\n'.join(lines)

        # Atomic write: write to temp file, then rename
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=self.learnbase_dir,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            # Atomic rename
            tmp_path.replace(self.file_path)
            logger.debug(f"Successfully wrote to {self.file_path}")

        except (IOError, OSError) as e:
            logger.error(f"Failed to write {self.file_path}: {e}")
            if tmp_path.exists():
                tmp_path.unlink()
            raise IOError(f"Failed to write to_learn.md: {e}") from e

    def add_topic(
        self,
        topic: str,
        context: str = "",
        detailed: bool = False,
        notes: str = ""
    ) -> None:
        """
        Add a new topic.

        Args:
            topic: Topic name
            context: What the topic is related to (e.g., "encryption", "networking")
            detailed: If True, add to detailed section; if False, add to quick table
            notes: Detailed notes (only used if detailed=True)

        Raises:
            ValueError: If validation fails or topic already exists
        """
        self._validate_topic_name(topic)

        data = self._parse_file()

        # Check for duplicates
        all_topics = data["quick"] + data["detailed"] + data["archived"]
        if any(t["topic"].lower() == topic.lower() for t in all_topics):
            raise ValueError(f"Topic '{topic}' already exists")

        added_date = datetime.now().strftime('%Y-%m-%d')

        new_topic = {
            "topic": topic,
            "added": added_date,
            "context": context,
            "detailed": detailed,
            "notes": notes if detailed else "",
            "archived": False
        }

        if detailed:
            data["detailed"].append(new_topic)
        else:
            data["quick"].append(new_topic)

        self._write_file(data)
        logger.info(f"Added {'detailed' if detailed else 'quick'} topic: {topic}")

    def list_topics(
        self,
        include_archived: bool = False
    ) -> List[Dict]:
        """
        List all topics with optional filtering.

        Args:
            include_archived: Include archived topics

        Returns:
            List of topic dictionaries
        """
        data = self._parse_file()
        topics = data["quick"] + data["detailed"]

        if include_archived:
            topics.extend(data["archived"])

        return topics

    def get_topic(self, topic: str) -> Optional[Dict]:
        """
        Get a specific topic by name.

        Args:
            topic: Topic name

        Returns:
            Topic dictionary or None if not found
        """
        self._validate_topic_name(topic)

        data = self._parse_file()
        all_topics = data["quick"] + data["detailed"] + data["archived"]

        for t in all_topics:
            if t["topic"].lower() == topic.lower():
                return t

        return None

    def remove_topic(self, topic: str) -> bool:
        """
        Archive a topic (move to archive section).

        Args:
            topic: Topic name

        Returns:
            True if archived, False if not found
        """
        self._validate_topic_name(topic)

        data = self._parse_file()

        # Find and remove from quick or detailed
        found = None
        for topic_list in [data["quick"], data["detailed"]]:
            for i, t in enumerate(topic_list):
                if t["topic"].lower() == topic.lower():
                    found = topic_list.pop(i)
                    break
            if found:
                break

        if not found:
            logger.warning(f"Topic '{topic}' not found for archival")
            return False

        # Add to archive
        found["archived"] = True
        found["completed"] = datetime.now().strftime('%Y-%m-%d')
        found["detailed"] = True  # All archived topics shown in detail
        data["archived"].append(found)

        self._write_file(data)
        logger.info(f"Archived topic: {topic}")
        return True

    def update_topic(
        self,
        topic: str,
        notes: Optional[str] = None,
        context: Optional[str] = None
    ) -> bool:
        """
        Update an existing topic.

        Args:
            topic: Topic name
            notes: New notes (optional)
            context: New context - what the topic is related to (optional)

        Returns:
            True if updated, False if not found
        """
        self._validate_topic_name(topic)

        data = self._parse_file()

        # Find topic
        found = None
        target_list = None
        for topic_list in [data["quick"], data["detailed"], data["archived"]]:
            for t in topic_list:
                if t["topic"].lower() == topic.lower():
                    found = t
                    target_list = topic_list
                    break
            if found:
                break

        if not found:
            logger.warning(f"Topic '{topic}' not found for update")
            return False

        # Update fields
        if notes is not None:
            found["notes"] = notes
            # If adding notes to a quick topic, convert to detailed
            if not found["detailed"] and notes.strip():
                found["detailed"] = True
                # Move from quick to detailed
                if target_list == data["quick"]:
                    data["quick"].remove(found)
                    data["detailed"].append(found)

        if context is not None:
            found["context"] = context

        self._write_file(data)
        logger.info(f"Updated topic: {topic}")
        return True

    def migrate_from_old_files(self, old_dir: Path) -> Dict[str, Any]:
        """
        Migrate topics from old file-based system.

        Args:
            old_dir: Directory containing old topic files

        Returns:
            Migration summary dictionary
        """
        old_dir = Path(old_dir)
        if not old_dir.exists() or not old_dir.is_dir():
            raise ValueError(f"Directory not found: {old_dir}")

        migrated = []
        failed = []

        # Read all .md files (except README)
        for file_path in old_dir.glob("*.md"):
            if file_path.name.lower() == "readme.md":
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Use filename (without .md) as topic name
                topic_name = file_path.stem

                # Add as detailed topic with content as notes
                self.add_topic(
                    topic=topic_name,
                    context=f"Migrated from {file_path.name}",
                    detailed=True,
                    notes=content.strip()
                )

                migrated.append(file_path.name)
                logger.info(f"Migrated: {file_path.name}")

            except Exception as e:
                logger.error(f"Failed to migrate {file_path.name}: {e}")
                failed.append({"file": file_path.name, "error": str(e)})

        # Create archive directory and move old files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_dir = self.learnbase_dir / f"to_learn_archived_{timestamp}"
        archive_dir.mkdir(parents=True, exist_ok=True)

        for file_path in old_dir.glob("*.md"):
            try:
                shutil.move(str(file_path), str(archive_dir / file_path.name))
            except Exception as e:
                logger.error(f"Failed to archive {file_path.name}: {e}")

        # Remove old directory if empty
        try:
            if not any(old_dir.iterdir()):
                old_dir.rmdir()
        except Exception as e:
            logger.warning(f"Could not remove old directory: {e}")

        summary = {
            "migrated_count": len(migrated),
            "failed_count": len(failed),
            "migrated_files": migrated,
            "failed_files": failed,
            "archive_location": str(archive_dir)
        }

        # Write migration log
        log_path = self.learnbase_dir / "to_learn_migration.log"
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"Migration completed at {datetime.now()}\n\n")
                f.write(f"Migrated: {len(migrated)} files\n")
                f.write(f"Failed: {len(failed)} files\n")
                f.write(f"Archive location: {archive_dir}\n\n")
                f.write("Migrated files:\n")
                for file in migrated:
                    f.write(f"  - {file}\n")
                if failed:
                    f.write("\nFailed files:\n")
                    for item in failed:
                        f.write(f"  - {item['file']}: {item['error']}\n")
        except Exception as e:
            logger.error(f"Failed to write migration log: {e}")

        logger.info(f"Migration complete: {len(migrated)} migrated, {len(failed)} failed")
        return summary
