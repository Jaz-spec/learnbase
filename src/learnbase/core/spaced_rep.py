"""Spaced repetition algorithm implementation (SM-2 simplified)."""

from datetime import datetime, timedelta
from typing import Tuple, List
import re


# SM-2 Spaced Repetition Algorithm Constants
# Based on the SuperMemo 2 algorithm with simplifications

# Ease Factor Constraints
EASE_FACTOR_MIN = 1.3  # Minimum ease factor (cards become no easier)
EASE_FACTOR_MAX = 3.0  # Maximum ease factor (prevents intervals becoming too long)
EASE_FACTOR_DEFAULT = 2.5  # Starting ease factor for new notes

# Ease Factor Adjustments (based on user rating)
EASE_DECREASE_POOR = 0.2  # Decrease for rating 1 (didn't remember)
EASE_DECREASE_FAIR = 0.15  # Decrease for rating 2 (barely remembered)
EASE_INCREASE_EXCELLENT = 0.1  # Increase for rating 4 (perfect recall)
# Note: Rating 3 (good) causes no ease factor change

# Interval Multipliers
INTERVAL_RESET_POOR = 1  # Reset to 1 day for rating 1
INTERVAL_REDUCE_FAIR = 0.5  # Halve interval for rating 2
INTERVAL_EXCELLENT_MULTIPLIER = 2.5  # 2.5x interval for rating 4
# Note: Rating 3 uses the ease factor as multiplier

# First Review Handling
FIRST_REVIEW_INTERVAL = 1  # First review always after 1 day for rating 3+


def calculate_next_review(
    rating: int,
    current_interval: int,
    ease_factor: float,
    review_count: int
) -> Tuple[int, float, datetime]:
    """
    Calculate the next review schedule based on SM-2 algorithm.

    Args:
        rating: User rating (1-4)
            1 (again): Didn't remember
            2 (hard): Barely remembered
            3 (good): Remembered well
            4 (easy): Perfect recall
        current_interval: Current interval in days
        ease_factor: Current ease factor (1.3 - 3.0)
        review_count: Number of times reviewed

    Returns:
        Tuple of (new_interval, new_ease_factor, next_review_date)
    """
    # Update ease factor based on rating
    new_ease_factor = ease_factor

    if rating == 1:
        new_ease_factor = max(EASE_FACTOR_MIN, ease_factor - EASE_DECREASE_POOR)
    elif rating == 2:
        new_ease_factor = max(EASE_FACTOR_MIN, ease_factor - EASE_DECREASE_FAIR)
    elif rating == 3:
        pass  # No change
    elif rating == 4:
        new_ease_factor = min(EASE_FACTOR_MAX, ease_factor + EASE_INCREASE_EXCELLENT)

    # Calculate new interval
    if rating == 1:
        new_interval = INTERVAL_RESET_POOR
    elif rating == 2:
        new_interval = max(1, int(current_interval * INTERVAL_REDUCE_FAIR))
    elif rating == 3:
        new_interval = int(current_interval * new_ease_factor) if review_count > 0 else FIRST_REVIEW_INTERVAL
    else:  # rating == 4
        new_interval = int(current_interval * INTERVAL_EXCELLENT_MULTIPLIER)

    # Calculate next review date
    next_review_date = datetime.now() + timedelta(days=new_interval)

    return new_interval, new_ease_factor, next_review_date


def parse_schedule_pattern(pattern: str) -> List[int]:
    """
    Parse schedule pattern string into list of day intervals.

    Args:
        pattern: Schedule pattern (e.g., "1d,1w,2w,1m,3m,6m")

    Returns:
        List of intervals in days

    Examples:
        "1d,1w,2w" -> [1, 7, 14]
        "1w,1m,3m" -> [7, 30, 90]
    """
    intervals = []
    parts = pattern.split(',')

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract number and unit
        match = re.match(r'(\d+)([dwmy])', part.lower())
        if not match:
            continue

        value = int(match.group(1))
        unit = match.group(2)

        # Convert to days
        if unit == 'd':
            days = value
        elif unit == 'w':
            days = value * 7
        elif unit == 'm':
            days = value * 30
        elif unit == 'y':
            days = value * 365
        else:
            continue

        intervals.append(days)

    return intervals if intervals else [1, 7, 14, 30]  # Default if parsing fails


def calculate_scheduled_review(
    rating: int,
    schedule_pattern: str,
    review_count: int
) -> Tuple[int, datetime]:
    """
    Calculate next review for scheduled mode.

    In scheduled mode, reviews follow a fixed pattern regardless of performance,
    but poor ratings can reset progress.

    Args:
        rating: User rating (1-4)
            1 (again): Reset to beginning of schedule
            2 (hard): Repeat current interval
            3 (good): Move to next interval
            4 (easy): Skip ahead in schedule
        schedule_pattern: Pattern like "1d,1w,2w,1m,3m,6m"
        review_count: Number of reviews completed

    Returns:
        Tuple of (interval_days, next_review_date)
    """
    intervals = parse_schedule_pattern(schedule_pattern)

    if rating == 1:
        # Reset to beginning
        next_interval = intervals[0]
    elif rating == 2:
        # Repeat current interval
        current_index = min(review_count, len(intervals) - 1)
        next_interval = intervals[current_index]
    elif rating == 3:
        # Move to next interval
        next_index = min(review_count + 1, len(intervals) - 1)
        next_interval = intervals[next_index]
    else:  # rating == 4
        # Skip ahead (but not past the end)
        next_index = min(review_count + 2, len(intervals) - 1)
        next_interval = intervals[next_index]

    next_review_date = datetime.now() + timedelta(days=next_interval)

    return next_interval, next_review_date


# Preset schedule patterns for scheduled review mode
# Usage: PRESET_SCHEDULES['moderate'] → "1d,1w,2w,1m,3m,6m"
PRESET_SCHEDULES = {
    "aggressive": "1d,3d,1w,2w,1m,3m",      # Intensive learning
    "moderate": "1d,1w,2w,1m,3m,6m",        # Recommended default
    "relaxed": "1w,2w,1m,2m,6m,1y"          # Long-term retention
}
