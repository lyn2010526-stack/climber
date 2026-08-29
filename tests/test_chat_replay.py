"""Tests for the authenticated chat replay contract."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1 import chat as chat_api
from app.core.agent_engine import AgentEngine


def _engine() -> AgentEngine:
    return AgentEngine(model_registry=object(), tool_registry=object())


@pytest.mark.asyncio
async def test_replay_endpoint_returns_empty_page_without_persisted_run(monkeypatch):
    engine = _engine()
    engine.create_session(
        agent_id="agent-1",
        user_id="user-1",
        provider="test",
        model_id="test-model",
        api_key="",
        session_id="replay-session",
    )
    monkeypatch.setattr(chat_api, "get_engine", lambda: engine)
    monkeypatch.setattr(chat_api, "_run_adapter", None)

    result = await chat_api.replay_chat_events(
        session_id="replay-session",
        after=1,
        turn_id="turn-1",
        limit=1,
        user_id="user-1",
    )

    assert result["session_id"] == "replay-session"
    assert result["after"] == 1
    assert result["run_id"] is None
    assert result["events"] == []
    assert result["oldest_sequence"] is None
    assert result["latest_sequence"] == 1


@pytest.mark.asyncio
async def test_replay_endpoint_enforces_session_owner(monkeypatch):
    engine = _engine()
    engine.create_session(
        agent_id="agent-1",
        user_id="owner",
        provider="test",
        model_id="test-model",
        api_key="",
        session_id="private-session",
    )
    monkeypatch.setattr(chat_api, "get_engine", lambda: engine)

    with pytest.raises(HTTPException) as error:
        await chat_api.replay_chat_events(
            session_id="private-session",
            user_id="other-user",
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_replay_endpoint_hides_unknown_sessions(monkeypatch):
    monkeypatch.setattr(chat_api, "get_engine", _engine)

    with pytest.raises(HTTPException) as error:
        await chat_api.replay_chat_events(session_id="missing", user_id="user-1")

    assert error.value.status_code == 404
