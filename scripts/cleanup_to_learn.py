#!/usr/bin/env python3
"""Cleanup script to fix archive section formatting."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from learnbase.core.to_learn_manager import ToLearnManager


def main():
    """Re-parse and re-write to clean up formatting."""
    manager = ToLearnManager()

    # Read current data
    data = manager._parse_file()

    print(f"Found {len(data['quick'])} quick topics")
    print(f"Found {len(data['detailed'])} detailed topics")
    print(f"Found {len(data['archived'])} archived topics")

    # Re-write (this will fix the formatting)
    manager._write_file(data)

    print("\n✓ File cleaned up successfully")


if __name__ == "__main__":
    main()
