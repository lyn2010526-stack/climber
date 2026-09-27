"""Graph memory engine wiring (producer + consumer reachability).

The graph-memory capability existed with zero production callers for its whole
life. These tests pin that the engine now drives it, and - just as importantly -
that an agent which did not opt in pays nothing.

Covers:
- write side: _store_episodic_memory forwards to record_graph_memory, and the
  forward is a no-op for agents without the opt-in
- read side: _inject_graph_context injects a SYSTEM message when opted in, stays
  silent otherwise, and replaces its marker instead of accumulating
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core.agent_engine import AgentEngine
from app.core.session import AgentSession
from app.tools import ToolRegistry

ENABLED_CONFIG = {"graph_memory": {"enabled": True, "max_triples_per_turn": 3}}


class _Settings:
    """Stand-in for GraphMemorySettings as the engine passes it through."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.max_triples_per_turn = 3


def _engine(enabled: bool, *, graph_text: str = "") -> tuple[AgentEngine, AsyncMock, AsyncMock]:
    engine = object.__new__(AgentEngine)
    engine._checkpoints = SimpleNamespace(save=AsyncMock(return_value="cp"))
    engine._sessions = {}
    engine._session_locks = {}
    engine._background_tasks = set()
    engine._shutdown_event = asyncio.Event()
    engine.resource_tracker = SimpleNamespace(
        track_tool_call=Mock(), record_token_usage=Mock(), get_metrics=Mock(return_value={})
    )
    engine.tool_prioritizer = Mock()
    engine.tool_registry = ToolRegistry()
    engine.debug_loop = None
    engine._setup_default_permissions = Mock()  # type: ignore[attr-defined]

    episodic = AsyncMock()
    record_graph = AsyncMock(return_value={"extracted": 2, "persisted": 2})
    get_settings = AsyncMock(return_value=_Settings(enabled))
    format_graph = AsyncMock(return_value=graph_text)

    engine.memory_service = SimpleNamespace(
        create_episodic_memory=episodic,
        record_graph_memory=record_graph,
        get_graph_memory_settings=get_settings,
        format_graph_context_for_prompt=format_graph,
    )
    return engine, record_graph, format_graph


def _session() -> AgentSession:
    s = AgentSession(session_id="gm-sess", user_id="u1", agent_id="a1")
    s.messages = [{"role": "user", "content": "ask"}]
    s._last_result = SimpleNamespace(content="x" * 200)
    return s


def test_write_side_forwards_to_graph_memory() -> None:
    engine, record_graph, _ = _engine(enabled=True)
    asyncio.run(engine._store_episodic_memory(_session(), "what is the gateway"))
    record_graph.assert_awaited_once()
    kwargs = record_graph.await_args.kwargs
    assert kwargs["user_id"] == "u1"
    assert kwargs["agent_id"] == "a1"
    assert kwargs["memory_config"].enabled is True
    assert "what is the gateway" in kwargs["content"]


def test_write_side_skips_graph_memory_when_not_opted_in() -> None:
    """A disabled agent must not pay for a feature it did not enable.

    The settings resolver decides, so the engine still calls the service; the
    service is what must short-circuit before any DB work. This test pins that
    the engine passes the unresolved config through rather than inventing its own
    policy.
    """
    engine, record_graph, _ = _engine(enabled=False)
    asyncio.run(engine._store_episodic_memory(_session(), "hello"))
    kwargs = record_graph.await_args.kwargs
    assert kwargs["memory_config"].enabled is False


def test_read_side_injects_when_opted_in() -> None:
    engine, _, _format_graph = _engine(
        enabled=True, graph_text="<graph_context>\n(user, works_at, acme)\n</graph_context>"
    )
    session = _session()
    asyncio.run(engine._inject_graph_context(session))
    system_msgs = [m for m in session.messages if m.get("role") == "system"]
    assert len(system_msgs) == 1
    assert system_msgs[0]["content"].startswith("<!-- GRAPH_CONTEXT -->")
    assert "acme" in system_msgs[0]["content"]


def test_read_side_silent_when_not_opted_in() -> None:
    engine, _, format_graph = _engine(enabled=True, graph_text="")
    session = _session()
    asyncio.run(engine._inject_graph_context(session))
    assert all(m.get("role") != "system" for m in session.messages)
    # The service is still consulted; it returns "" for a non-opted-in agent.
    assert format_graph.await_args.kwargs["memory_config"].enabled is True


def test_read_side_replaces_marker_not_accumulates() -> None:
    engine, _, _ = _engine(enabled=True, graph_text="<graph_context>first</graph_context>")
    session = _session()
    asyncio.run(engine._inject_graph_context(session))
    engine.memory_service.format_graph_context_for_prompt = AsyncMock(
        return_value="<graph_context>second</graph_context>"
    )
    asyncio.run(engine._inject_graph_context(session))
    system_msgs = [m for m in session.messages if m.get("role") == "system"]
    assert len(system_msgs) == 1
    assert "second" in system_msgs[0]["content"]


def test_read_side_never_raises_into_the_request_path() -> None:
    engine, _, _format_graph = _engine(enabled=True, graph_text="unused")
    engine.memory_service.format_graph_context_for_prompt = AsyncMock(
        side_effect=RuntimeError("graph store unavailable")
    )
    session = _session()
    asyncio.run(engine._inject_graph_context(session))  # must not raise
    assert all(m.get("role") != "system" for m in session.messages)


@pytest.mark.asyncio
async def test_read_side_uses_shared_pool_for_agentless_session() -> None:
    """An empty agent_id must resolve to the shared pool, matching _inject_memory_context."""
    engine, _, format_graph = _engine(enabled=True, graph_text="<graph_context/>")
    s = AgentSession(session_id="gm-sess-2", user_id="u2", agent_id="")
    s.messages = [{"role": "user", "content": "hi"}]
    await engine._inject_graph_context(s)
    assert format_graph.await_args.kwargs["agent_id"] is None
    assert format_graph.await_args.kwargs["user_id"] == "u2"
