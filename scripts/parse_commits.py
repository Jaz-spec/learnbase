#!/usr/bin/env python3
"""
Parse git commits from a repository and output as markdown or write to project files.

This script supports two modes:

1. Print Mode (default): Prints commits to terminal
2. Project Mode (--project): Writes commits to ~/.learnbase/active-context/<project>.md

Usage:
    # Print to terminal
    python parse_commits.py --repo /path/to/repo --since 2025-01-25 --until 2025-02-02
    python parse_commits.py --repo /path/to/repo --since 7d  # Last 7 days

    # Write to project file (auto-detects week from oldest commit)
    python parse_commits.py --repo /path/to/repo --since 7d --project learnbase

    # Write to project file (explicit week grouping)
    python parse_commits.py --repo /path/to/repo --since 2026-01-27 --until 2026-02-02 --project learnbase --week-of 2026-01-27

Project File Format:
    Project files are stored at ~/.learnbase/active-context/<project>.md with the following structure:
    - Header with repo path, status, timestamps
    - Current Context section (user-editable)
    - Commit History with week-based sections (newest first)
    - Reflection placeholder for each week

    Completed projects can be moved to ~/.learnbase/active-context/archive/
"""

import argparse
import subprocess
import sys
import tempfile
import re
from datetime import datetime
from pathlib import Path


def validate_repo(repo_path: str) -> Path:
    """Validate that the path is a git repository."""
    repo = Path(repo_path).resolve()

    if not repo.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    git_dir = repo / ".git"
    if not git_dir.exists():
        raise ValueError(f"Not a git repository: {repo_path}")

    return repo


def parse_git_log(repo_path: Path, since: str = None, until: str = None, branch: str = "main") -> list[dict]:
    """
    Parse git log from repository.

    Args:
        repo_path: Path to git repository
        since: Start date (YYYY-MM-DD or relative like '7d')
        until: End date (YYYY-MM-DD)
        branch: Branch name (default: main)

    Returns:
        List of commit dictionaries with hash, author, date, message
    """
    # Build git log command
    cmd = [
        "git",
        "-C", str(repo_path),
        "log",
        "--format=%H|%an|%ai|%s",  # hash|author|date|subject
        branch
    ]

    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")

    # Execute command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git command failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git command timed out after 30 seconds")

    # Parse output
    commits = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue

        parts = line.split('|', 3)
        if len(parts) != 4:
            print(f"Warning: Skipping malformed git log line: {line}", file=sys.stderr)
            continue

        commit_hash, author, date, message = parts

        commits.append({
            'hash': commit_hash[:7],  # Short hash
            'full_hash': commit_hash,
            'author': author,
            'date': date,
            'message': message
        })

    return commits


def format_as_markdown(commits: list[dict], repo_path: Path, since: str = None, until: str = None) -> str:
    """
    Format commits as markdown.

    Args:
        commits: List of commit dictionaries
        repo_path: Path to repository
        since: Start date for header
        until: End date for header

    Returns:
        Markdown formatted string
    """
    if not commits:
        return "No commits found in the specified date range."

    # Build header
    repo_name = repo_path.name
    date_range = ""
    if since and until:
        date_range = f" ({since} to {until})"
    elif since:
        date_range = f" (since {since})"

    md = f"## {repo_name}{date_range}\n\n"
    md += f"**{len(commits)} commit{'s' if len(commits) != 1 else ''}:**\n\n"

    # Add commits
    for commit in commits:
        md += f"- `{commit['hash']}` - {commit['message']}\n"

    return md


def get_week_start(date_str: str = None) -> str:
    """
    Get the Monday of the week for a given date.

    Args:
        date_str: Date string (YYYY-MM-DD) or None for current week

    Returns:
        Monday date as YYYY-MM-DD string
    """
    if date_str:
        date = datetime.fromisoformat(date_str)
    else:
        date = datetime.now()

    # Get Monday of the week (weekday 0 = Monday)
    days_since_monday = date.weekday()
    monday = date.replace(hour=0, minute=0, second=0, microsecond=0)
    monday = monday.replace(day=date.day - days_since_monday)

    return monday.strftime('%Y-%m-%d')


def ensure_directory_exists(dir_path: Path):
    """
    Ensure directory exists, creating it if necessary.

    Args:
        dir_path: Path to directory
    """
    dir_path.mkdir(parents=True, exist_ok=True)


def get_active_context_dir() -> Path:
    """Get the active-context directory path."""
    return Path.home() / '.learnbase' / 'active-context'


def find_project_file(project_name: str) -> Path | None:
    """
    Find project file by name (case-insensitive).

    Args:
        project_name: Project name (without .md extension)

    Returns:
        Path to project file if exists, None otherwise
    """
    context_dir = get_active_context_dir()
    if not context_dir.exists():
        return None

    # Try exact match first
    exact_match = context_dir / f"{project_name}.md"
    if exact_match.exists():
        return exact_match

    # Try case-insensitive match
    for file in context_dir.glob("*.md"):
        if file.stem.lower() == project_name.lower():
            return file

    return None


def create_project_file(project_name: str, repo_path: Path) -> Path:
    """
    Create new project file with template.

    Args:
        project_name: Project name
        repo_path: Path to git repository

    Returns:
        Path to created file
    """
    context_dir = get_active_context_dir()
    ensure_directory_exists(context_dir)

    # Use title case for project name in file
    project_title = project_name.replace('-', ' ').replace('_', ' ').title()
    file_path = context_dir / f"{project_name}.md"

    today = datetime.now().strftime('%Y-%m-%d')

    template = f"""# {project_title}

**Repository:** {repo_path}
**Status:** active
**Created:** {today}
**Last Updated:** {today}

## Current Context

[Add your project context here: goal, approach, feature set]

## Commit History

"""

    file_path.write_text(template)
    return file_path


def format_week_section(week_of: str, commits: list[dict]) -> str:
    """
    Format commits as a week section.

    Args:
        week_of: Week start date (YYYY-MM-DD)
        commits: List of commit dictionaries

    Returns:
        Formatted markdown section
    """
    section = f"### Week of {week_of}\n\n"

    for commit in commits:
        section += f"- `{commit['hash']}` - {commit['message']}\n"

    section += "\n**Reflection:** [To be added during weekly review]\n\n"

    return section


def append_commits_section(file_path: Path, week_of: str, commits: list[dict]):
    """
    Append commits section to project file.

    Args:
        file_path: Path to project file
        week_of: Week start date (YYYY-MM-DD)
        commits: List of commit dictionaries
    """
    # Read existing content
    content = file_path.read_text()

    # Find the "## Commit History" section
    history_match = re.search(r'^## Commit History\s*$', content, re.MULTILINE)
    if not history_match:
        raise ValueError("Project file missing '## Commit History' section")

    # Check if this week already exists
    week_pattern = re.escape(f"### Week of {week_of}")
    if re.search(week_pattern, content):
        print(f"Warning: Week of {week_of} already exists in file. Skipping.", file=sys.stderr)
        return

    # Split content at Commit History section
    history_pos = history_match.end()
    before_history = content[:history_pos]
    after_history = content[history_pos:]

    # Format new week section
    new_section = "\n" + format_week_section(week_of, commits)

    # Insert new section after "## Commit History" header
    new_content = before_history + new_section + after_history

    # Update "Last Updated" timestamp
    today = datetime.now().strftime('%Y-%m-%d')
    new_content = re.sub(
        r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
        f'**Last Updated:** {today}',
        new_content
    )

    # Write atomically (temp file + rename)
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=file_path.parent,
        delete=False,
        prefix='.tmp_',
        suffix='.md'
    ) as tmp_file:
        tmp_file.write(new_content)
        tmp_path = Path(tmp_file.name)

    # Atomic rename
    tmp_path.replace(file_path)


def write_to_project_file(
    project_name: str,
    repo_path: Path,
    commits: list[dict],
    week_of: str = None
):
    """
    Write commits to project file.

    Args:
        project_name: Project name
        repo_path: Path to git repository
        commits: List of commit dictionaries
        week_of: Week start date (YYYY-MM-DD), auto-detected from oldest commit if not specified
    """
    if not commits:
        print("No commits to write.", file=sys.stderr)
        return

    # Determine week - use oldest commit date if not specified
    if not week_of:
        # Get oldest commit (last in list, since git log is newest-first)
        oldest_commit_date = commits[-1]['date']
        # Parse ISO date (format: 2026-01-27 12:34:56 +0000)
        date_part = oldest_commit_date.split()[0]  # Get YYYY-MM-DD part
        week_of = get_week_start(date_part)

    # Find or create project file
    file_path = find_project_file(project_name)
    if file_path:
        print(f"Appending to existing project file: {file_path}")
    else:
        file_path = create_project_file(project_name, repo_path)
        print(f"Created new project file: {file_path}")

    # Append commits section
    append_commits_section(file_path, week_of, commits)
    print(f"Added {len(commits)} commit(s) for week of {week_of}")


def main():
    parser = argparse.ArgumentParser(
        description="Parse git commits and output as markdown or write to project file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Print to terminal (default)
  %(prog)s --repo /path/to/repo --since 2025-01-25 --until 2025-02-02
  %(prog)s --repo /path/to/repo --since 7d

  # Write to project file
  %(prog)s --repo /path/to/repo --since 7d --project learnbase
  %(prog)s --repo /path/to/repo --since 2026-01-27 --until 2026-02-02 --project learnbase --week-of 2026-01-27

  # Specify branch
  %(prog)s --repo /path/to/repo --since 7d --branch develop
        """
    )

    parser.add_argument(
        '--repo',
        required=True,
        help='Path to git repository'
    )

    parser.add_argument(
        '--since',
        help='Start date (YYYY-MM-DD or relative like "7d", "1w")'
    )

    parser.add_argument(
        '--until',
        help='End date (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--branch',
        default='main',
        help='Branch name (default: main)'
    )

    parser.add_argument(
        '--format',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown). Only used in print mode.'
    )

    parser.add_argument(
        '--project',
        help='Project name to write commits to file (e.g., "learnbase"). Creates/updates ~/.learnbase/active-context/<project>.md'
    )

    parser.add_argument(
        '--week-of',
        help='Week start date (YYYY-MM-DD) for grouping commits. Defaults to current week if not specified.'
    )

    args = parser.parse_args()

    try:
        # Validate repository
        repo_path = validate_repo(args.repo)

        # Parse commits
        commits = parse_git_log(
            repo_path,
            since=args.since,
            until=args.until,
            branch=args.branch
        )

        # Write to project file or print to stdout
        if args.project:
            write_to_project_file(
                args.project,
                repo_path,
                commits,
                week_of=args.week_of
            )
        else:
            # Format output
            if args.format == 'json':
                import json
                output = json.dumps(commits, indent=2)
            else:
                output = format_as_markdown(commits, repo_path, args.since, args.until)

            # Print to stdout
            print(output)

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == '__main__':
    main()
