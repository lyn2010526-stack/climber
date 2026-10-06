"""Coverage tests for app.core.engine.pregel.streaming."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.core.engine.pregel.streaming import (
    StreamEvent,
    StreamEventType,
    StreamManager,
    stream_events,
)


def test_stream_event_types_and_to_dict() -> None:
    assert StreamEventType.UPDATES.value == "updates"
    assert StreamEventType.VALUES.value == "values"
    assert StreamEventType.CUSTOM.value == "custom"
    event = StreamEvent(type=StreamEventType.VALUES, data={"a": 1}, node="n", step=3)
    d = event.to_dict()
    assert d["type"] == "values"
    assert d["data"] == {"a": 1}
    assert d["node"] == "n"
    assert d["step"] == 3
    assert d["timestamp"] == event.timestamp.isoformat()


async def test_stream_manager_emit_to_subscriber() -> None:
    mgr = StreamManager()

    async def consume() -> list[StreamEvent]:
        received = []
        async for event in mgr.subscribe():
            received.append(event)
        return received

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await mgr.emit(StreamEvent(type=StreamEventType.UPDATES, data={"x": 1}))
    await mgr.close()
    received = await task
    assert len(received) == 1
    assert received[0].data == {"x": 1}


async def test_stream_manager_emit_after_close_is_noop() -> None:
    mgr = StreamManager()
    await mgr.close()
    await mgr.emit(StreamEvent(type=StreamEventType.UPDATES, data={}))
    # only the close sentinel remains in the internal queue
    assert mgr._queue.qsize() == 1
    assert (await mgr._queue.get()) is None


async def test_stream_manager_close_idempotent() -> None:
    mgr = StreamManager()
    await mgr.close()
    await mgr.close()
    assert mgr._closed is True
    assert (await mgr._queue.get()) is None


async def test_stream_manager_close_handles_queue_empty_race() -> None:
    class _FlakyQueue:
        def __init__(self) -> None:
            self.puts: list[Any] = []

        def empty(self) -> bool:
            return False

        def get_nowait(self) -> Any:
            raise asyncio.QueueEmpty

        async def put(self, item: Any) -> None:
            self.puts.append(item)

    mgr = StreamManager()
    flaky = _FlakyQueue()
    mgr._queue = flaky  # type: ignore[assignment]
    await mgr.close()
    assert mgr._closed is True
    assert flaky.puts == [None]


async def test_stream_values_success() -> None:
    mgr = StreamManager()

    async def execute(_inp: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"step": 1}
        yield {"step": 2}

    emitted: list[StreamEvent] = []

    async def consume() -> None:
        async for event in mgr.subscribe():
            emitted.append(event)

    import asyncio

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await mgr.stream_values({"in": 1}, execute)
    await task
    types = [e.type for e in emitted]
    assert types[0] == StreamEventType.START
    assert types[-1] == StreamEventType.END
    assert sum(1 for t in types if t == StreamEventType.VALUES) == 2


async def test_stream_values_error_propagates() -> None:
    mgr = StreamManager()

    async def execute(_inp: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        raise RuntimeError("boom")
        yield {}  # pragma: no cover

    with pytest.raises(RuntimeError, match="boom"):
        await mgr.stream_values({}, execute)


async def test_stream_updates_success() -> None:
    mgr = StreamManager()

    async def execute(
        _inp: dict[str, Any],
    ) -> AsyncIterator[tuple[dict[str, Any], str | None, int]]:
        yield {"delta": 1}, "n", 1

    emitted: list[StreamEvent] = []

    async def consume() -> None:
        async for event in mgr.subscribe():
            emitted.append(event)

    import asyncio

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await mgr.stream_updates({}, execute)
    await task
    assert any(e.type == StreamEventType.UPDATES and e.node == "n" for e in emitted)


async def test_stream_updates_error_propagates() -> None:
    mgr = StreamManager()

    async def execute(
        _inp: dict[str, Any],
    ) -> AsyncIterator[tuple[dict[str, Any], str | None, int]]:
        raise ValueError("bad")
        yield {}, None, 0  # pragma: no cover

    with pytest.raises(ValueError, match="bad"):
        await mgr.stream_updates({}, execute)


async def test_stream_events_helper_values_and_updates() -> None:
    async def gen() -> AsyncIterator[tuple[dict[str, Any], str | None, int]]:
        yield {"a": 1}, "n1", 1
        yield {"b": 2}, None, 2

    values = [e async for e in stream_events(gen(), mode="values")]
    assert all(e.type == StreamEventType.VALUES for e in values)
    assert values[0].node == "n1"

    updates = [e async for e in stream_events(gen(), mode="updates")]
    assert all(e.type == StreamEventType.UPDATES for e in updates)
