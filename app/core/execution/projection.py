"""Pure projections rebuilt from the execution event log."""

from __future__ import annotations

from typing import Any, Iterable

from app.core.execution.event_bus import TaskEvent


_STATUS_BY_EVENT = {
    "created": "created",
    "started": "running",
    "paused": "paused",
    "resumed": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


def project_task_state(events: Iterable[TaskEvent]) -> dict[str, Any] | None:
    """Fold an ordered event stream into a small task state projection.

    The function has no storage, clock, or mutable external dependency. An
    empty stream returns ``None`` so callers can distinguish no task from a
    task with an incomplete lifecycle.
    """
    state: dict[str, Any] | None = None
    for event in events:
        if state is None:
            state = {
                "task_id": event.task_id,
                "status": "unknown",
                "event_count": 0,
                "last_event_id": None,
                "last_sequence": None,
            }
        if event.task_id != state["task_id"]:
            raise ValueError("a task projection cannot combine multiple task ids")
        state["event_count"] += 1
        state["last_event_id"] = event.event_id
        state["last_sequence"] = event.sequence
        if event.event_type in _STATUS_BY_EVENT:
            state["status"] = _STATUS_BY_EVENT[event.event_type]
    return state
