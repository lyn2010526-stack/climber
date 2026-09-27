"""Structured logging for contained agent-engine failures."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.core import agent_engine as engine_mod
from app.core.session import AgentSession


def test_observability_sink_failure_is_logged_and_contained(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(engine_mod, "logger", logger)

    import app.core.observability.api as observability_api

    def broken_sinks():
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(observability_api, "get_trace_collector", broken_sinks)

    assert engine_mod._observability_sinks() == (None, None)
    logger.warning.assert_called_once_with(
        "observability_sinks_unavailable",
        error="storage unavailable",
        error_type="RuntimeError",
    )


def test_alignment_tracker_failure_is_logged_and_contained(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(engine_mod, "logger", logger)

    import app.core.observability.api as observability_api

    monkeypatch.setattr(
        observability_api,
        "get_goal_tracker",
        Mock(side_effect=LookupError("tracker missing")),
    )

    assert engine_mod._alignment_tracker() is None
    logger.warning.assert_called_once_with(
        "alignment_tracker_unavailable",
        error="tracker missing",
        error_type="LookupError",
    )


@pytest.mark.asyncio
async def test_span_end_failure_is_logged_without_breaking_run(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(engine_mod, "logger", logger)
    collector = Mock()
    collector.start_span.return_value = object()
    collector.end_span.side_effect = RuntimeError("trace backend stopped")
    monkeypatch.setattr(engine_mod, "_observability_sinks", lambda: (collector, None))
    monkeypatch.setattr(engine_mod, "_alignment_tracker", lambda: None)

    engine = engine_mod.AgentEngine.__new__(engine_mod.AgentEngine)
    engine._session_locks = {}

    async def run_locked(session, message):
        yield engine_mod.AgentEvent(type=engine_mod.AgentEventType.DONE, data={})

    monkeypatch.setattr(engine, "_run_locked", run_locked)
    session = AgentSession(session_id="s-span", agent_id="a", user_id="u")

    produced = [event async for event in engine.run(session, "hello")]

    assert len(produced) == 1
    logger.warning.assert_called_once_with(
        "trace_span_end_failed",
        session_id="s-span",
        status="ok",
        error="trace backend stopped",
        error_type="RuntimeError",
    )


def test_context_binding_failures_are_logged_and_contained(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(engine_mod, "logger", logger)
    session = AgentSession(session_id="s-context", agent_id="a", user_id="u")

    monkeypatch.setattr(
        "app.core.file_patch.set_current_agent_mode",
        Mock(side_effect=RuntimeError("mode unavailable")),
    )
    monkeypatch.setattr(
        "app.core.memory_context.set_memory_scope",
        Mock(side_effect=RuntimeError("scope unavailable")),
    )

    engine = engine_mod.AgentEngine.__new__(engine_mod.AgentEngine)
    engine._set_agent_mode(session)
    engine._set_memory_scope(session)

    assert [call.args[0] for call in logger.warning.call_args_list] == [
        "agent_mode_binding_failed",
        "memory_scope_binding_failed",
    ]
    assert logger.warning.call_args_list[0].kwargs["session_id"] == "s-context"
    assert logger.warning.call_args_list[1].kwargs["agent_id"] == "a"
