"""Coverage tests for app.core.execution.event_bus."""

from __future__ import annotations

from app.core.execution import event_bus as event_bus_module
from app.core.execution.event_bus import (
    EventBus,
    TaskEvent,
    get_task_event_bus,
    reset_task_event_bus,
)


def test_task_event_to_dict() -> None:
    event = TaskEvent(event_type="started", task_id="t1", data={"a": 1})
    d = event.to_dict()
    assert d["event_type"] == "started"
    assert d["task_id"] == "t1"
    assert d["data"] == {"a": 1}
    assert "event_id" in d and "timestamp" in d


async def test_publish_persists_and_history_filters() -> None:
    bus = EventBus()
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_STARTED, task_id="t1"))
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_COMPLETED, task_id="t1"))
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_STARTED, task_id="t2"))

    assert len(bus.get_history()) == 3
    assert len(bus.get_history(task_id="t1")) == 2
    assert len(bus.get_history(event_type=EventBus.EVENT_STARTED)) == 2
    assert len(bus.get_history(task_id="t1", event_type=EventBus.EVENT_COMPLETED)) == 1
    assert bus.get_history(limit=1)[0].event_type == EventBus.EVENT_STARTED

    bus.clear_history()
    assert bus.get_history() == []
    bus.close()


async def test_subscribe_sync_and_async_handlers() -> None:
    bus = EventBus()
    seen: list[str] = []

    def sync_handler(event: TaskEvent) -> None:
        seen.append(f"sync:{event.task_id}")

    async def async_handler(event: TaskEvent) -> None:
        seen.append(f"async:{event.task_id}")

    bus.subscribe(EventBus.EVENT_STARTED, sync_handler)
    bus.subscribe(EventBus.EVENT_STARTED, async_handler)
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_STARTED, task_id="t"))
    assert seen == ["sync:t", "async:t"]

    assert bus.unsubscribe(EventBus.EVENT_STARTED, sync_handler) is True
    assert bus.unsubscribe(EventBus.EVENT_STARTED, sync_handler) is False
    bus.close()


async def test_publish_swallows_handler_errors() -> None:
    bus = EventBus()

    def bad_handler(event: TaskEvent) -> None:
        raise RuntimeError("handler-boom")

    bus.subscribe(EventBus.EVENT_STARTED, bad_handler)
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_STARTED, task_id="t"))
    assert len(bus.get_history(task_id="t")) == 1
    bus.close()


async def test_get_pending_task_ids() -> None:
    bus = EventBus()
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_CREATED, task_id="pending"))
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_STARTED, task_id="running"))
    await bus.publish(TaskEvent(event_type=EventBus.EVENT_COMPLETED, task_id="done"))
    assert set(bus.get_pending_task_ids()) == {"pending", "running"}
    bus.close()


def test_close_is_idempotent() -> None:
    bus = EventBus()
    bus.close()
    bus.close()
    assert bus._closed is True


def test_file_backed_bus_creates_parent_dir(tmp_path) -> None:
    db = tmp_path / "nested" / "events.db"
    bus = EventBus(db_path=str(db))
    assert db.exists()
    bus.close()


def test_singleton_get_and_reset(tmp_path, monkeypatch) -> None:
    reset_task_event_bus()
    monkeypatch.setattr(
        event_bus_module,
        "_default_event_bus_path",
        tmp_path / "default.db",
    )
    bus1 = get_task_event_bus()
    bus2 = get_task_event_bus()
    assert bus1 is bus2
    reset_task_event_bus()
    bus3 = get_task_event_bus()
    assert bus3 is not bus1
    bus3.close()
    reset_task_event_bus()
    # explicit memory path
    mem = get_task_event_bus(db_path=":memory:")
    assert mem is not None
    reset_task_event_bus()
