"""Bounded in-memory replay storage for agent event streams."""

from __future__ import annotations

import copy
import json
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReplayRecord:
    sequence: int
    event_id: str
    turn_id: str
    event_type: str
    data: dict[str, Any]


class EventReplayBuffer:
    """Retain a bounded suffix of events for reconnect and diagnostics."""

    def __init__(self, capacity: int = 256, max_bytes: int = 256 * 1024) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.capacity = capacity
        self.max_bytes = max_bytes
        self._events: deque[tuple[ReplayRecord, int]] = deque()
        self._next_sequence = 1
        self._total_bytes = 0

    def append(self, event_type: str, data: dict[str, Any], turn_id: str = "") -> ReplayRecord:
        sequence = self._next_sequence
        self._next_sequence += 1
        record = ReplayRecord(
            sequence=sequence,
            event_id=f"event-{sequence}",
            turn_id=turn_id,
            event_type=event_type,
            data=copy.deepcopy(data),
        )
        size = len(json.dumps(record.data, ensure_ascii=False, default=str).encode("utf-8"))
        self._events.append((record, size))
        self._total_bytes += size
        self._evict()
        return record

    def after(self, sequence: int = 0, turn_id: str | None = None) -> list[ReplayRecord]:
        """Return retained events strictly after a client cursor."""
        return [
            record
            for record, _ in self._events
            if record.sequence > sequence and (turn_id is None or record.turn_id == turn_id)
        ]

    @property
    def oldest_sequence(self) -> int | None:
        return self._events[0][0].sequence if self._events else None

    @property
    def latest_sequence(self) -> int:
        return self._next_sequence - 1

    def _evict(self) -> None:
        while self._events and (
            len(self._events) > self.capacity or self._total_bytes > self.max_bytes
        ):
            _, size = self._events.popleft()
            self._total_bytes -= size
