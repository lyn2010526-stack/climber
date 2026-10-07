"""M1 event replay and pure projection tests."""

from app.core.execution.event_bus import EventBus, TaskEvent
from app.core.execution.projection import project_task_state


async def test_replay_returns_append_order_and_supports_cursor(tmp_path) -> None:
    bus = EventBus(db_path=str(tmp_path / "events.db"))
    await bus.publish(TaskEvent("created", "task-1"))
    await bus.publish(TaskEvent("started", "task-1"))
    await bus.publish(TaskEvent("completed", "task-1"))

    events = bus.replay(task_id="task-1")
    assert [event.event_type for event in events] == ["created", "started", "completed"]
    assert [event.sequence for event in events] == [1, 2, 3]
    assert [event.event_type for event in bus.replay(task_id="task-1", after_sequence=1)] == [
        "started",
        "completed",
    ]
    bus.close()


async def test_projection_rebuilds_task_state_from_events() -> None:
    events = [
        TaskEvent("created", "task-1", sequence=1),
        TaskEvent("started", "task-1", sequence=2),
        TaskEvent("completed", "task-1", sequence=3),
    ]

    assert project_task_state(events) == {
        "task_id": "task-1",
        "status": "completed",
        "event_count": 3,
        "last_event_id": events[-1].event_id,
        "last_sequence": 3,
    }
    assert project_task_state([]) is None


async def test_projection_rejects_mixed_tasks() -> None:
    events = [TaskEvent("created", "task-1"), TaskEvent("created", "task-2")]

    try:
        project_task_state(events)
    except ValueError as error:
        assert "multiple task ids" in str(error)
    else:
        raise AssertionError("mixed task ids must be rejected")
