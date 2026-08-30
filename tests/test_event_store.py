"""Tests for the persistent append-only EventStore."""

from __future__ import annotations

import pytest

from app.core.integration.event_sourcing import EventSourcedStore, EventSourcingManager
from app.core.integration.event_store import EventStore


@pytest.mark.asyncio
async def test_append_returns_unified_envelope(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        event = await store.append("message", {"content": "hello"}, stream_id="s1")

        assert event["event_id"]
        assert event["event_type"] == "message"
        assert event["stream_id"] == "s1"
        assert event["sequence"] == 1
        assert event["ts"] > 0
        assert event["data"] == {"content": "hello"}
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_sequences_are_globally_monotonic_across_streams(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        first = await store.append("a", {}, stream_id="s1")
        second = await store.append("b", {}, stream_id="s2")
        third = await store.append("a", {}, stream_id="s1")

        assert [first["sequence"], second["sequence"], third["sequence"]] == [1, 2, 3]
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_events_survive_reopen(tmp_path):
    path = tmp_path / "events.db"
    store = EventStore(path)
    await store.append("message", {"content": "persisted"}, stream_id="s1")
    await store.close()

    reopened = EventStore(path)
    try:
        events = await reopened.read(stream_id="s1")
        assert len(events) == 1
        assert events[0]["data"] == {"content": "persisted"}

        resumed = await reopened.append("message", {"content": "next"}, stream_id="s1")
        assert resumed["sequence"] == 2
    finally:
        await reopened.close()


@pytest.mark.asyncio
async def test_read_filters_by_type_and_sequence(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        await store.append("message", {"n": 1}, stream_id="s1")
        await store.append("tool_call", {"n": 2}, stream_id="s1")
        await store.append("message", {"n": 3}, stream_id="s1")
        await store.append("message", {"n": 4}, stream_id="s2")

        by_type = await store.read(stream_id="s1", event_type="message")
        assert [e["data"]["n"] for e in by_type] == [1, 3]

        after = await store.read(after_sequence=2)
        assert [e["data"]["n"] for e in after] == [3, 4]

        assert await store.count() == 4
        assert await store.count(stream_id="s1") == 3
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_non_serializable_data_falls_back_to_str(tmp_path):
    store = EventStore(tmp_path / "events.db")
    try:
        event = await store.append("misc", {"obj": object()}, stream_id="s1")
        assert isinstance(event["data"]["obj"], str)

        events = await store.read(stream_id="s1")
        assert isinstance(events[0]["data"]["obj"], str)
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_manager_persists_and_restores_stream(tmp_path):
    path = tmp_path / "events.db"

    async def apply_counter(state, event):
        if event.get("type") == "inc":
            return (state or 0) + 1
        return state or 0

    store = EventStore(path)
    mgr = EventSourcingManager(event_store=store)
    mgr.register_store(EventSourcedStore(name="counter", apply=apply_counter, initial_state=0))
    await mgr.emit("inc", {})
    await mgr.emit("inc", {})
    await store.close()

    restored_store = EventStore(path)
    restored = EventSourcingManager(event_store=restored_store)
    restored.register_store(EventSourcedStore(name="counter", apply=apply_counter, initial_state=0))
    try:
        await restored.restore()
        snap = await restored.snapshot()
        assert snap["counter"] == 2
    finally:
        await restored_store.close()


@pytest.mark.asyncio
async def test_arch_v2_integration_uses_persistent_event_store(monkeypatch, tmp_path):
    from app import main

    monkeypatch.setattr(main.settings, "enable_arch_v2", True)
    monkeypatch.setattr(main.settings, "enable_integration", True)
    monkeypatch.setattr(main, "BASE_DIR", tmp_path)

    handles = await main._init_arch_v2()
    assert handles is not None
    event_store = handles["event_store"]
    try:
        assert isinstance(event_store, EventStore)
        assert event_store._path == tmp_path / "data" / "events.db"

        await handles["event_sourcing_manager"].emit("message", {"content": "hi"})
        assert await event_store.count() == 1
    finally:
        await event_store.close()
