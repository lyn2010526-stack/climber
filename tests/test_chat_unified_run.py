"""Integration tests: Chat endpoint drives AgentEngine through the unified Run adapter."""

from __future__ import annotations

import pytest

from app.api.v1 import chat as chat_api
from app.core import ChatResult
from app.core.agent_engine import AgentEngine
from app.models.registry import ModelRegistry
from app.storage import async_session
from app.storage.database import Session as SessionModel
from app.tools import ToolRegistry
from tests.test_agent_engine import FakeModelAdapter, _FakeMemory, _noop_persist

SESSION_ID = "chat-unified-run-session"


def _build_engine() -> AgentEngine:
    from app.core.permission_rules import PermissionConfig, PermissionMode

    engine = AgentEngine(model_registry=ModelRegistry(), tool_registry=ToolRegistry())
    engine.model_registry._models["openai:gpt-4o-mini"] = FakeModelAdapter(
        responses=[ChatResult(content="hello from run", finish_reason="stop")]
    )
    engine._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)
    engine.debug_loop = None
    engine.memory_service = _FakeMemory()
    engine._persist_message = _noop_persist
    return engine


async def _create_session_row() -> None:
    async with async_session() as db:
        existing = await db.get(SessionModel, SESSION_ID)
        if existing is None:
            db.add(SessionModel(id=SESSION_ID, user_id="user-1", title="unified run"))
            await db.commit()


async def _chat_once(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    engine = _build_engine()
    monkeypatch.setattr(chat_api, "get_engine", lambda: engine)
    monkeypatch.setattr(chat_api, "_run_adapter", None)
    await _create_session_row()

    response = await chat_api.chat(
        session_id=SESSION_ID,
        request=chat_api.ChatRequest(message="hello"),
        user_id="user-1",
    )
    chunks = [chunk async for chunk in response.body_iterator]
    names: list[str] = []
    for chunk in chunks:
        first_line = chunk.splitlines()[0]
        assert first_line.startswith("event: ")
        names.append(first_line.removeprefix("event: "))
    return names


@pytest.mark.asyncio
async def test_chat_streams_legacy_event_names_via_unified_run(monkeypatch):
    names = await _chat_once(monkeypatch)

    assert names == ["thinking", "text", "checkpoint", "done"]


@pytest.mark.asyncio
async def test_chat_replay_serves_persisted_run_events_with_same_identifiers(monkeypatch):
    await _chat_once(monkeypatch)
    engine = chat_api.get_engine()

    replay = await chat_api.replay_chat_events(
        session_id=SESSION_ID,
        after=0,
        turn_id=None,
        limit=256,
        user_id="user-1",
    )

    assert replay["run_id"] is not None
    assert [event["event"] for event in replay["events"]] == ["thinking", "text", "checkpoint", "done"]
    assert [event["sequence"] for event in replay["events"]] == [1, 2, 3, 4]
    assert all(event["turn_id"] == replay["run_id"] for event in replay["events"])
    assert replay["events"][1]["data"]["content"] == "hello from run"

    by_turn = await chat_api.replay_chat_events(
        session_id=SESSION_ID,
        after=0,
        turn_id=replay["run_id"],
        limit=256,
        user_id="user-1",
    )
    assert [event["event_id"] for event in by_turn["events"]] == [event["event_id"] for event in replay["events"]]

    in_memory = engine.replay_events(engine._sessions[SESSION_ID])
    assert [record.event_type for record in in_memory] == [event["event"] for event in replay["events"]]


@pytest.mark.asyncio
async def test_two_sequential_chats_create_two_runs(monkeypatch):
    await _chat_once(monkeypatch)

    names = await _chat_once(monkeypatch)

    assert names == ["thinking", "text", "checkpoint", "done"]
    replay = await chat_api.replay_chat_events(
        session_id=SESSION_ID,
        after=0,
        turn_id=None,
        limit=256,
        user_id="user-1",
    )
    assert replay["run_id"] is not None
