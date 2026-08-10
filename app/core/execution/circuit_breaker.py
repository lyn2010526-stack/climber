"""Timeout manager and circuit breaker for task execution.

Provides:
- CircuitBreaker: CLOSED -> OPEN -> HALF_OPEN state machine
- TimeoutManager: per-task timeout tracking with automatic failure
"""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

logger = logging.getLogger(__name__)


class CircuitBreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    max_failures: int = 5
    recovery_timeout: float = 60.0
    failure_window: float = 300.0


@dataclass
class CircuitBreakerRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: str = CircuitBreakerState.CLOSED.value
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tripped_at: str = ""


class CircuitBreaker:
    """Circuit breaker for task execution failure protection.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, config: CircuitBreakerConfig | None = None, name: str = "default"):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_timestamps: list[float] = []
        self._last_failure_time = 0.0
        self._last_state_change = datetime.now(UTC)
        self._tripped_at: datetime | None = None

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN:
            if self._should_try_recovery():
                self._transition_to(CircuitBreakerState.HALF_OPEN)
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitBreakerState.OPEN

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def _should_try_recovery(self) -> bool:
        if self._last_failure_time == 0:
            return False
        return (time.time() - self._last_failure_time) >= self.config.recovery_timeout

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.now(UTC)
        if new_state == CircuitBreakerState.OPEN:
            self._tripped_at = datetime.now(UTC)
            logger.warning("circuit_breaker_tripped: breaker=%s failures=%d", self.name, self._failure_count)
        elif new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._failure_timestamps.clear()
            self._tripped_at = None
        logger.info(
            "circuit_breaker_state_change: breaker=%s from=%s to=%s",
            self.name,
            old_state.value,
            new_state.value,
        )

    def record_success(self) -> None:
        self._success_count += 1
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.CLOSED)

    def record_failure(self) -> bool:
        now = time.time()
        self._failure_count += 1
        self._failure_timestamps.append(now)
        self._last_failure_time = now
        window_start = now - self.config.failure_window
        self._failure_timestamps = [t for t in self._failure_timestamps if t >= window_start]
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.OPEN)
            return True
        if len(self._failure_timestamps) >= self.config.max_failures:
            self._transition_to(CircuitBreakerState.OPEN)
            return True
        return False

    def allow_request(self) -> bool:
        current_state = self.state
        if current_state == CircuitBreakerState.CLOSED:
            return True
        if current_state == CircuitBreakerState.HALF_OPEN:
            return True
        return False

    def get_record(self) -> CircuitBreakerRecord:
        return CircuitBreakerRecord(
            state=self._state.value,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_state_change=self._last_state_change.isoformat(),
            tripped_at=self._tripped_at.isoformat() if self._tripped_at else "",
        )

    def reset(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._failure_timestamps.clear()
        self._last_failure_time = 0.0
        self._last_state_change = datetime.now(UTC)
        self._tripped_at = None


class TimeoutManager:
    """Tracks per-task timeouts and triggers failure on expiration."""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_timeouts (
                task_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                timeout_seconds INTEGER NOT NULL,
                deadline TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running'
            );
        """)
        self._conn.commit()

    def start_task(self, task_id: str, timeout_seconds: int) -> None:
        now = datetime.now(UTC)
        deadline = (now + timedelta(seconds=timeout_seconds)).isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO task_timeouts
            (task_id, started_at, timeout_seconds, deadline, status)
            VALUES (?, ?, ?, ?, 'running')
            """,
            (task_id, now.isoformat(), timeout_seconds, deadline),
        )
        self._conn.commit()

    def check_timeout(self, task_id: str) -> bool:
        row = self._conn.execute(
            "SELECT * FROM task_timeouts WHERE task_id = ? AND status = 'running'",
            (task_id,),
        ).fetchone()
        if not row:
            return False
        deadline = datetime.fromisoformat(row["deadline"])
        return datetime.now(UTC) > deadline

    def complete_task(self, task_id: str) -> None:
        self._conn.execute(
            "UPDATE task_timeouts SET status = 'completed' WHERE task_id = ?",
            (task_id,),
        )
        self._conn.commit()

    def fail_task(self, task_id: str) -> None:
        self._conn.execute(
            "UPDATE task_timeouts SET status = 'failed' WHERE task_id = ?",
            (task_id,),
        )
        self._conn.commit()

    def get_timed_out_tasks(self) -> list[str]:
        now = datetime.now(UTC).isoformat()
        rows = self._conn.execute(
            "SELECT task_id FROM task_timeouts WHERE status = 'running' AND deadline <= ?",
            (now,),
        ).fetchall()
        return [row["task_id"] for row in rows]

    def get_remaining_time(self, task_id: str) -> float:
        row = self._conn.execute(
            "SELECT deadline FROM task_timeouts WHERE task_id = ? AND status = 'running'",
            (task_id,),
        ).fetchone()
        if not row:
            return 0.0
        deadline = datetime.fromisoformat(row["deadline"])
        remaining = (deadline - datetime.now(UTC)).total_seconds()
        return max(0.0, remaining)

    def close(self) -> None:
        self._conn.close()
