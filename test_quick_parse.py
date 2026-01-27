#!/usr/bin/env python3
"""Test quick topic parsing fix."""

from pathlib import Path
from src.learnbase.core.to_learn_manager import ToLearnManager

# Initialize manager
manager = ToLearnManager()

# List topics
topics = manager.list_topics()

# Separate quick and detailed
quick = [t for t in topics if not t.get("detailed")]
detailed = [t for t in topics if t.get("detailed")]

print(f"Quick topics: {len(quick)}")
print(f"Detailed topics: {len(detailed)}")
print(f"Total: {len(topics)}")

print("\nQuick topics:")
for t in quick:
    print(f"  - {t['topic']} ({t.get('context', 'no context')})")

print("\nDetailed topics:")
for t in detailed:
    print(f"  - {t['topic']}")
