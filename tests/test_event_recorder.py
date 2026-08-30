"""Tests for the unified runtime event recorder."""

from __future__ import annotations

from typing import Any

import pytest

from app.core import AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.integration.event_store import EventStore
from app.core.integration.recorder import (
    clear_event_store,
    record,
    set_event_store,
)
from app.core.task_state_machine import TaskState
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry
from tests.test_agent_engine import FakeModelAdapter


@pytest.fixture(autouse=True)
def _clean_recorder():
    clear_event_store()
    yield
    clear_event_store()


@pytest.mark.asyncio
async def test_record_noop_without_store():
    await record("s1", "message", {"role": "user"})


@pytest.mark.asyncio
async def test_record_appends_to_store(tmp_path):
    store = EventStore(tmp_path / "events.db")
    set_event_store(store)
    try:
        await record("s1", "message", {"role": "user", "content": "hi"})
        events = await store.read(stream_id="s1")
        assert [(e["event_type"], e["data"]["role"]) for e in events] == [
            ("message", "user")
        ]
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_record_swallows_store_errors():
    class _Boom:
        async def append(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("disk exploded")

    set_event_store(_Boom())
    await record("s1", "message", {"role": "user"})


@pytest.mark.asyncio
async def test_attach_session_recorder_records_transitions(tmp_path):
    store = EventStore(tmp_path / "events.db")
    set_event_store(store)
    try:
        engine = AgentEngine(model_registry=ModelRegistry(), tool_registry=ToolRegistry())
        session = engine.create_session(
            agent_id="a", user_id="u", provider="p", model_id="m", api_key="k",
        )

        await session.state_machine.transition(TaskState.PROCESSING, trigger="run_start")
        await session.state_machine.transition(TaskState.COMPLETED, trigger="run_complete")

        events = await store.read(stream_id=session.session_id, event_type="session_state")
        assert [(e["data"]["from"], e["data"]["to"]) for e in events] == [
            ("pending", "processing"),
            ("processing", "completed"),
        ]
    finally:
        await store.close()


def _engine() -> AgentEngine:
    engine = AgentEngine(model_registry=ModelRegistry(), tool_registry=ToolRegistry())
    engine.debug_loop = None

    class _FakeMemory:
        async def format_memories_for_prompt(self, user_id: str, query: str, max_memories: int = 5) -> str:
            return ""

        async def create_episodic_memory(self, **kwargs: Any) -> None:
            return None

    engine.memory_service = _FakeMemory()
    return engine


@pytest.mark.asyncio
async def test_persist_message_records_event(tmp_path):
    store = EventStore(tmp_path / "events.db")
    set_event_store(store)
    try:
        engine = _engine()

        async def _noop_flush(session_id: str) -> None:
            engine._msg_buffers.pop(session_id, None)

        engine._flush_buffer = _noop_flush  # type: ignore[method-assign]
        await engine._persist_message("s1", "user", content="hello", run_id="r1")

        events = await store.read(stream_id="s1", event_type="message")
        assert len(events) == 1
        assert events[0]["data"]["role"] == "user"
        assert events[0]["data"]["content"] == "hello"
        assert events[0]["data"]["run_id"] == "r1"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_run_loop_records_lifecycle_events_but_not_text_chunks(tmp_path):
    store = EventStore(tmp_path / "events.db")
    set_event_store(store)
    try:
        engine = _engine()

        async def _noop_persist(*args: Any, **kwargs: Any) -> None:
            return None

        engine._persist_message = _noop_persist  # type: ignore[method-assign]
        engine.model_registry._models["fake:fake-model"] = FakeModelAdapter()
        session = engine.create_session(
            agent_id="a", user_id="u", provider="fake", model_id="fake-model", api_key="k",
        )
        engine.register_session(session)

        async for _event in engine.run(session, "hello"):
            pass

        events = await store.read(stream_id=session.session_id)
        types = [e["event_type"] for e in events]

        assert AgentEventType.DONE.value in types
        assert AgentEventType.THINKING.value in types
        assert AgentEventType.TEXT.value not in types
        assert "session_state" in types
    finally:
        await store.close()
