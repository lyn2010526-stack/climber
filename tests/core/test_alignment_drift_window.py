"""Tests for the alignment drift window.

``alignment_checks.timestamp`` stores ISO 8601 with a ``T`` separator and a
``+00:00`` offset, e.g. ``2026-09-26T11:00:44.362745+00:00``. The drift query
compared that against SQLite's ``datetime('now', '-1 hour')``, which produces
``2026-09-26 13:00:44``. A space sorts before ``T``, so every stored timestamp
compared greater than the cutoff regardless of age: a check recorded three
hours ago still counted as recent, and the drift score never reflected it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.observability.alignment import GoalTracker


def _record(tracker: GoalTracker, score: float, age_hours: float) -> None:
    stamp = (datetime.now(UTC) - timedelta(hours=age_hours)).isoformat()
    tracker._conn.execute(
        "INSERT INTO alignment_checks (goal_id, current_action, alignment_score, timestamp, notes)"
        " VALUES (?, ?, ?, ?, ?)",
        ("goal-1", "acting", score, stamp, ""),
    )
    tracker._conn.commit()


def test_stale_record_is_not_counted_as_recent(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "a.db"))
    # A well-aligned check, but recorded three hours ago.
    _record(tracker, score=1.0, age_hours=3)

    assert tracker.get_drift_score() == 0.0, "a stale check must not count"


def test_fresh_record_drives_the_score(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "b.db"))
    _record(tracker, score=0.5, age_hours=0.1)

    assert tracker.get_drift_score() == 0.5


def test_window_boundary_excludes_records_just_outside_one_hour(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "c.db"))
    _record(tracker, score=0.2, age_hours=1.5)

    assert tracker.get_drift_score() == 0.0


def test_mixed_ages_average_only_the_recent_ones(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "d.db"))
    _record(tracker, score=1.0, age_hours=5)   # stale, perfectly aligned
    _record(tracker, score=0.5, age_hours=0.5)  # recent, half aligned

    # Only the recent 0.5 counts, so drift is 0.5 rather than 0.25.
    assert tracker.get_drift_score() == 0.5


def test_no_checks_reports_no_drift(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "e.db"))
    assert tracker.get_drift_score() == 0.0


def test_score_is_clamped_to_unit_range(tmp_path):
    tracker = GoalTracker(db_path=str(tmp_path / "f.db"))
    _record(tracker, score=1.0, age_hours=0.1)
    assert 0.0 <= tracker.get_drift_score() <= 1.0


def test_alignment_goal_and_check_are_read_after_restart(tmp_path):
    db_path = str(tmp_path / "restart.db")
    first = GoalTracker(db_path=db_path)
    goal = first.register_goal("ship the release", keywords=["ship", "release"])
    checks = first.check_alignment("ship the release")

    reopened = GoalTracker(db_path=db_path)

    restored_goal = reopened.get_goal(goal.id)
    history = reopened.get_alignment_history(goal_id=goal.id)

    assert restored_goal is not None
    assert restored_goal.description == "ship the release"
    assert len(checks) == 1
    assert len(history) == 1
    assert history[0].goal_id == goal.id
    assert history[0].alignment_score == 1.0
