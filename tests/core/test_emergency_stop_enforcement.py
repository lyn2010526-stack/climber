"""Emergency stop enforcement tests.

`EmergencyStop` (app/core/observability/emergency_stop.py) documents that
activating it "blocks all new task executions" and "signals running tasks to
cancel". Neither was true: `is_activated()` had no caller in any executor, so
the REST endpoints could flip a flag that nothing read. The store also
defaults to `db_path=":memory:"`, so the state did not even survive a restart.

These tests pin the enforcement path: the engine refuses to start a run while
stopped, a stopped run is reported distinctly from a model error, and the
state persists when a real database path is used.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def stop():
    from app.core.observability.emergency_stop import EmergencyStopManager

    instance = EmergencyStopManager()
    yield instance
    if instance.is_activated():
        instance.deactivate(triggered_by="test-cleanup")


def test_a_fresh_stop_is_not_activated(stop) -> None:
    assert stop.is_activated() is False


def test_activating_makes_the_flag_visible(stop) -> None:
    stop.activate(reason="test", triggered_by="tester")
    assert stop.is_activated() is True


def test_deactivating_clears_the_flag(stop) -> None:
    stop.activate(reason="test", triggered_by="tester")
    stop.deactivate(triggered_by="tester")
    assert stop.is_activated() is False


def test_the_engine_gate_reports_activated(stop) -> None:
    from app.core.observability.emergency_stop import is_emergency_stop_active

    stop.activate(reason="test", triggered_by="tester")

    assert is_emergency_stop_active(stop) is True


def test_the_engine_gate_reports_clear_when_idle(stop) -> None:
    from app.core.observability.emergency_stop import is_emergency_stop_active

    assert is_emergency_stop_active(stop) is False


def test_state_survives_a_new_instance_on_the_same_database(tmp_path) -> None:
    """An in-memory store loses the flag on restart, which defeats the point."""
    from app.core.observability.emergency_stop import EmergencyStopManager

    db = str(tmp_path / "stop.db")
    first = EmergencyStopManager(db_path=db)
    first.activate(reason="incident", triggered_by="ops")

    second = EmergencyStopManager(db_path=db)
    assert second.is_activated() is True
    second.deactivate(triggered_by="ops-cleanup")


@pytest.mark.asyncio
async def test_a_stopped_run_yields_an_error_event_and_no_model_call() -> None:
    """The gate has to stop execution, not merely annotate the response.

    The engine reads the process-wide manager, so the test has to activate
    that one. A private instance would leave the gate inactive and the run
    would proceed to the model, which is exactly the bug being fixed.
    """
    from app.core import AgentEventType, MessageRole
    from app.core.agent_engine import AgentEngine
    from app.core.observability import emergency_stop as es
    from app.core.session import AgentSession

    shared = es.get_emergency_stop()
    shared.activate(reason="incident", triggered_by="ops")

    class ExplodingRegistry:
        def get_tool(self, name):
            raise AssertionError("the run must not reach tool resolution")

    engine = AgentEngine.__new__(AgentEngine)
    engine.tool_registry = ExplodingRegistry()
    engine.sandbox = None
    engine.permission_overlay = None
    engine.agent_mode = None
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    engine.max_sessions = 4

    session = AgentSession(session_id="s", agent_id="a", user_id="u")
    session.messages.append({"role": MessageRole.USER, "content": "hi"})

    events = []
    async for event in engine.run(session, "hi"):
        events.append(event)
        break

    assert events, "the run produced no event at all"
    assert events[0].type == AgentEventType.ERROR
    assert "emergency" in str(events[0].data).lower()

    shared.deactivate(triggered_by="test-cleanup")


@pytest.mark.asyncio
async def test_an_idle_stop_lets_the_run_proceed_past_the_gate() -> None:
    """The gate must not block normal execution."""
    from app.core import MessageRole
    from app.core.agent_engine import AgentEngine
    from app.core.observability import emergency_stop as es
    from app.core.session import AgentSession

    shared = es.get_emergency_stop()
    if shared.is_activated():
        shared.deactivate(triggered_by="test-setup")

    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    engine._session_locks = {}
    engine._session_order = []
    engine.max_sessions = 4
    engine.sandbox = None
    engine.permission_overlay = None
    engine.agent_mode = None
    engine.tool_registry = None

    session = AgentSession(session_id="s2", agent_id="a", user_id="u")
    session.messages.append({"role": MessageRole.USER, "content": "hi"})

    events = []
    async for event in engine.run(session, "hi"):
        events.append(event)
        break

    assert events, "an idle stop produced no event"
    assert "emergency" not in str(events[0].data).lower()
