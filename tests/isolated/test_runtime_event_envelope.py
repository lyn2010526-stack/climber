"""Isolated tests for the runtime lifecycle event envelope."""

from __future__ import annotations

from app.core.execution.event_bus import EventBus, TaskEvent
from app.core.task_worker import TaskManager


async def test_event_bus_assigns_persistent_sequence_and_envelope_fields(tmp_path) -> None:
    database = tmp_path / "events.db"
    first = EventBus(db_path=str(database))
    event = TaskEvent(
        event_type="subtask_completed",
        task_id="task-1",
        data={"subtask_id": "child-1"},
        correlation_id="task-1",
        producer="task_manager",
    )
    await first.publish(event)
    assert event.sequence == 1
    first.close()

    second = EventBus(db_path=str(database))
    await second.publish(TaskEvent(event_type="task_update", task_id="task-1"))
    history = second.get_history(task_id="task-1", limit=10)
    assert [item.sequence for item in reversed(history)] == [1, 2]
    assert history[-1].correlation_id == "task-1"
    assert history[-1].schema_version == 1
    assert history[-1].producer == "task_manager"
    second.close()


async def test_task_manager_bridges_events_to_event_bus() -> None:
    bus = EventBus()
    manager = TaskManager(max_workers=1, event_bus=bus)

    await manager.emit_event("task-1", "subtask_completed", {"subtask_id": "child-1"})
    await manager.emit_event("task-1", "task_update", {"status": "completed"})

    events = bus.get_history(task_id="task-1", limit=10)
    assert [event.event_type for event in reversed(events)] == [
        "subtask_completed",
        "task_update",
    ]
    oldest, newest = reversed(events)
    assert newest.causation_id == oldest.event_id
    assert newest.correlation_id == "task-1"
    assert newest.producer == "task_manager"
    assert manager._event_history["task-1"][-1]["event_id"] == newest.event_id
    bus.close()
