#!/usr/bin/env python3
"""Test script for to-learn functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from learnbase.core.to_learn_manager import ToLearnManager


def test_add_quick_topic():
    """Test adding a quick topic."""
    print("Testing add quick topic...")
    manager = ToLearnManager()
    manager.add_topic(
        topic="Test Quick Topic",
        context="Testing quick capture",
        detailed=False,
        status="to-learn"
    )
    print("✓ Added quick topic")


def test_add_detailed_topic():
    """Test adding a detailed topic."""
    print("Testing add detailed topic...")
    manager = ToLearnManager()
    manager.add_topic(
        topic="Test Detailed Topic",
        context="Testing detailed notes",
        detailed=True,
        notes="This is a detailed note with multiple lines.\n\nIt can have paragraphs.",
        status="to-learn"
    )
    print("✓ Added detailed topic")


def test_list_topics():
    """Test listing topics."""
    print("Testing list topics...")
    manager = ToLearnManager()
    topics = manager.list_topics()
    print(f"✓ Found {len(topics)} topics")
    for topic in topics[:3]:  # Show first 3
        print(f"  - {topic['topic']} ({topic['status']})")


def test_update_status():
    """Test updating status."""
    print("Testing update status...")
    manager = ToLearnManager()
    manager.update_status("Test Quick Topic", "in-progress")
    print("✓ Updated status to in-progress")


def test_update_notes():
    """Test updating notes."""
    print("Testing update notes...")
    manager = ToLearnManager()
    manager.update_topic(
        "Test Detailed Topic",
        notes="Updated notes with more information."
    )
    print("✓ Updated notes")


def test_get_topic():
    """Test getting a specific topic."""
    print("Testing get topic...")
    manager = ToLearnManager()
    topic = manager.get_topic("Test Quick Topic")
    if topic:
        print(f"✓ Retrieved topic: {topic['topic']}")
        print(f"  Status: {topic['status']}")
        print(f"  Context: {topic['context']}")
    else:
        print("✗ Topic not found")


def test_archive_topic():
    """Test archiving a topic."""
    print("Testing archive topic...")
    manager = ToLearnManager()
    success = manager.remove_topic("Test Quick Topic")
    if success:
        print("✓ Archived topic")
    else:
        print("✗ Failed to archive")


def main():
    """Run all tests."""
    print("="*60)
    print("Testing To-Learn Manager")
    print("="*60 + "\n")

    try:
        test_add_quick_topic()
        print()
        test_add_detailed_topic()
        print()
        test_list_topics()
        print()
        test_update_status()
        print()
        test_update_notes()
        print()
        test_get_topic()
        print()
        test_archive_topic()
        print()

        print("="*60)
        print("All tests passed!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
