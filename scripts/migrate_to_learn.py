#!/usr/bin/env python3
"""
One-time migration script to convert old to_learn files to new format.

Usage:
    python scripts/migrate_to_learn.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from learnbase.core.to_learn_manager import ToLearnManager


def main():
    """Run migration from old file-based system to new single-file system."""
    old_dir = Path.home() / ".learnbase" / "to_learn"

    if not old_dir.exists():
        print(f"No migration needed: {old_dir} does not exist")
        return

    if not old_dir.is_dir():
        print(f"Error: {old_dir} is not a directory")
        return

    # Check if there are any .md files to migrate
    md_files = list(old_dir.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {old_dir}")
        return

    print(f"Found {len(md_files)} files to migrate:")
    for f in md_files:
        print(f"  - {f.name}")

    print("\nStarting migration...")

    # Initialize ToLearnManager (creates new to_learn.md if needed)
    manager = ToLearnManager()

    # Run migration
    try:
        summary = manager.migrate_from_old_files(old_dir)

        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Successfully migrated: {summary['migrated_count']} files")
        print(f"Failed: {summary['failed_count']} files")
        print(f"Archive location: {summary['archive_location']}")

        if summary['migrated_files']:
            print("\nMigrated files:")
            for file in summary['migrated_files']:
                print(f"  ✓ {file}")

        if summary['failed_files']:
            print("\nFailed files:")
            for item in summary['failed_files']:
                print(f"  ✗ {item['file']}: {item['error']}")

        print("\n" + "="*60)
        print(f"Migration log saved to: ~/.learnbase/to_learn_migration.log")
        print(f"New to-learn file: ~/.learnbase/to_learn.md")
        print("="*60)

    except Exception as e:
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
