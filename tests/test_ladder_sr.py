"""Tests for ladder-based spaced repetition (drill card SR)."""

from datetime import datetime, timedelta

from src.learnbase.core.spaced_rep import (
    calculate_ladder_review,
    LADDER_INTERVALS,
    REWRITE_FAIL_THRESHOLD,
)


class TestLadderProgression:
    def test_pass_from_step_zero_advances(self):
        step, interval, next_date, fs = calculate_ladder_review(
            passed=True, current_step=0, fail_streak=0
        )
        assert step == 1
        assert interval == LADDER_INTERVALS[1]
        assert fs == 0

    def test_fail_resets_fail_streak_increment(self):
        step, interval, next_date, fs = calculate_ladder_review(
            passed=False, current_step=3, fail_streak=1
        )
        assert step == 2
        assert interval == LADDER_INTERVALS[2]
        assert fs == 2

    def test_pass_clears_fail_streak(self):
        _, _, _, fs = calculate_ladder_review(
            passed=True, current_step=2, fail_streak=5
        )
        assert fs == 0

    def test_pass_at_max_step_stays_capped(self):
        max_step = len(LADDER_INTERVALS) - 1
        step, interval, _, _ = calculate_ladder_review(
            passed=True, current_step=max_step, fail_streak=0
        )
        assert step == max_step
        assert interval == LADDER_INTERVALS[max_step]

    def test_fail_at_step_zero_floors(self):
        step, interval, _, fs = calculate_ladder_review(
            passed=False, current_step=0, fail_streak=4
        )
        assert step == 0
        assert interval == LADDER_INTERVALS[0]
        assert fs == 5  # still increments even at the floor

    def test_next_review_date_matches_interval(self):
        step, interval, next_date, _ = calculate_ladder_review(
            passed=True, current_step=2, fail_streak=0
        )
        expected = datetime.now() + timedelta(days=interval)
        # allow ~1 second of drift for the datetime.now() calls
        assert abs((next_date - expected).total_seconds()) < 2

    def test_fail_streak_crosses_rewrite_threshold(self):
        # simulate three consecutive fails starting from step 3
        step, fs = 3, 0
        for _ in range(REWRITE_FAIL_THRESHOLD):
            step, _, _, fs = calculate_ladder_review(
                passed=False, current_step=step, fail_streak=fs
            )
        assert fs == REWRITE_FAIL_THRESHOLD
        # caller uses fs >= threshold to flag needs_rewrite

    def test_ladder_is_monotonic_increasing(self):
        """Sanity: the ladder intervals should increase; otherwise SR is broken."""
        for a, b in zip(LADDER_INTERVALS, LADDER_INTERVALS[1:]):
            assert a < b


class TestLadderSequence:
    """End-to-end: walk a card through pass/fail patterns and verify state."""

    def test_all_pass_reaches_top(self):
        step, fs = 0, 0
        for _ in range(len(LADDER_INTERVALS) + 3):  # +3 to confirm cap holds
            step, _, _, fs = calculate_ladder_review(
                passed=True, current_step=step, fail_streak=fs
            )
        assert step == len(LADDER_INTERVALS) - 1
        assert fs == 0

    def test_alternating_stays_low(self):
        step, fs = 0, 0
        for passed in [True, False, True, False, True, False]:
            step, _, _, fs = calculate_ladder_review(
                passed=passed, current_step=step, fail_streak=fs
            )
        # after three pass+fail pairs we net zero progression
        assert step == 0
