"""Goal alignment verification.

Tracks agent goals and verifies that current actions remain
aligned with registered objectives. Detects drift when actions
deviate from intended goals.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AlignmentCheck:
    """Result of a single alignment verification."""

    goal_id: str = ""
    current_action: str = ""
    alignment_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "current_action": self.current_action,
            "alignment_score": self.alignment_score,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class Goal:
    """A registered goal for alignment tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    priority: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "keywords": self.keywords,
            "priority": self.priority,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }


class GoalTracker:
    """Tracks goals and verifies action alignment.

    Compares current agent actions against registered goals using
    keyword overlap and semantic heuristics. Drift is detected
    when the alignment score falls below the configured threshold.
    """

    def __init__(self, db_path: str = ":memory:", alignment_threshold: float = 0.7):
        self._db_path = db_path
        self._alignment_threshold = alignment_threshold
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                keywords_json TEXT NOT NULL DEFAULT '[]',
                priority INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS alignment_checks (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                current_action TEXT NOT NULL,
                alignment_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_alignment_goal
                ON alignment_checks(goal_id);
        """)
        self._conn.commit()

    def register_goal(
        self,
        description: str,
        keywords: list[str] | None = None,
        priority: int = 1,
    ) -> Goal:
        """Register a new goal for alignment tracking."""
        goal = Goal(
            description=description,
            keywords=keywords or self._extract_keywords(description),
            priority=priority,
        )
        self._persist_goal(goal)
        return goal

    def deactivate_goal(self, goal_id: str) -> bool:
        """Deactivate a goal so it is no longer checked."""
        row = self._conn.execute("SELECT id FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            return False
        self._conn.execute(
            "UPDATE goals SET is_active = 0 WHERE id = ?", (goal_id,)
        )
        self._conn.commit()
        return True

    def get_goal(self, goal_id: str) -> Goal | None:
        """Retrieve a goal by ID."""
        row = self._conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if not row:
            return None
        return self._row_to_goal(row)

    def list_goals(self, active_only: bool = True) -> list[Goal]:
        """List all goals, optionally filtering to active only."""
        if active_only:
            rows = self._conn.execute(
                "SELECT * FROM goals WHERE is_active = 1 ORDER BY priority DESC"
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM goals ORDER BY priority DESC").fetchall()
        return [self._row_to_goal(row) for row in rows]

    def check_alignment(self, current_action: str) -> list[AlignmentCheck]:
        """Check alignment of current action against all active goals."""
        goals = self.list_goals(active_only=True)
        results = []
        for goal in goals:
            score = self._compute_alignment(current_action, goal)
            check = AlignmentCheck(
                goal_id=goal.id,
                current_action=current_action,
                alignment_score=score,
                notes=self._generate_notes(score),
            )
            self._persist_check(check)
            results.append(check)
        return results

    def get_drift_score(self) -> float:
        """Compute overall drift score across all recent alignment checks.

        Returns 0.0 (fully aligned) to 1.0 (fully drifted).
        """
        rows = self._conn.execute(
            """
            SELECT goal_id, AVG(alignment_score) as avg_score
            FROM alignment_checks
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY goal_id
            """
        ).fetchall()
        if not rows:
            return 0.0
        avg_scores = [row["avg_score"] for row in rows]
        overall_avg = sum(avg_scores) / len(avg_scores)
        return max(0.0, min(1.0, 1.0 - overall_avg))

    def get_alignment_history(
        self, goal_id: str | None = None, limit: int = 50
    ) -> list[AlignmentCheck]:
        """Retrieve alignment check history."""
        if goal_id:
            rows = self._conn.execute(
                "SELECT * FROM alignment_checks WHERE goal_id = ? ORDER BY timestamp DESC LIMIT ?",
                (goal_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM alignment_checks ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_check(row) for row in rows]

    def is_aligned(self, current_action: str) -> bool:
        """Quick check: is the current action aligned with any active goal?"""
        checks = self.check_alignment(current_action)
        if not checks:
            return True
        return max(c.alignment_score for c in checks) >= self._alignment_threshold

    def _compute_alignment(self, action: str, goal: Goal) -> float:
        """Compute alignment score between an action and a goal.

        Uses keyword overlap as a simple heuristic.
        Returns a score between 0.0 (no alignment) and 1.0 (perfect alignment).
        """
        if not goal.keywords:
            return 0.5

        action_lower = action.lower()
        action_words = set(re.findall(r'\w+', action_lower))
        if not action_words:
            return 0.0

        keyword_matches = sum(
            1 for kw in goal.keywords if kw.lower() in action_lower or kw.lower() in action_words
        )
        return min(1.0, keyword_matches / max(1, len(goal.keywords)))

    def _generate_notes(self, score: float) -> str:
        if score >= self._alignment_threshold:
            return "aligned"
        if score >= self._alignment_threshold * 0.5:
            return "partial_alignment"
        return "drift_detected"

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r'\w+', text.lower())
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "not", "no", "this", "that", "it", "its",
        }
        return [w for w in words if w not in stopwords and len(w) > 2]

    def _persist_goal(self, goal: Goal) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO goals
            (id, description, keywords_json, priority, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                goal.id,
                goal.description,
                json.dumps(goal.keywords),
                goal.priority,
                goal.created_at,
                1 if goal.is_active else 0,
            ),
        )
        self._conn.commit()

    def _persist_check(self, check: AlignmentCheck) -> None:
        self._conn.execute(
            """
            INSERT INTO alignment_checks
            (id, goal_id, current_action, alignment_score, timestamp, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                check.goal_id,
                check.current_action,
                check.alignment_score,
                check.timestamp,
                check.notes,
            ),
        )
        self._conn.commit()

    def _row_to_goal(self, row: sqlite3.Row) -> Goal:
        return Goal(
            id=row["id"],
            description=row["description"],
            keywords=json.loads(row["keywords_json"]),
            priority=row["priority"],
            created_at=row["created_at"],
            is_active=bool(row["is_active"]),
        )

    def _row_to_check(self, row: sqlite3.Row) -> AlignmentCheck:
        return AlignmentCheck(
            goal_id=row["goal_id"],
            current_action=row["current_action"],
            alignment_score=row["alignment_score"],
            timestamp=row["timestamp"],
            notes=row["notes"],
        )

    def close(self) -> None:
        self._conn.close()
