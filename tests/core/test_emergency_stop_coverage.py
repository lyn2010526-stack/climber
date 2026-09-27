"""Emergency stop coverage across every execution entry point.

The kill switch was only consulted in ``AgentEngine.run``. Workflow runs, crew
executions and the two collaboration entry points started work regardless, so
activating the stop did not actually halt a running deployment.

All four now go through ``emergency_stop.execution_blocked``, the single gate
shared with the engine.
"""

from __future__ import annotations

import pytest

from app.core.observability import emergency_stop as es
from app.multi_agent import TaskStatus


@pytest.fixture
def stopped(tmp_path):
    """Activate the kill switch on a private store and hand back the manager."""
    manager = es.EmergencyStopManager(db_path=str(tmp_path / "stop.db"))
    manager.activate(reason="test", triggered_by="tester")
    es.set_emergency_stop(manager)
    yield manager
    es.set_emergency_stop(None)


def _reset() -> None:
    es.set_emergency_stop(None)


def test_execution_blocked_reports_while_active(stopped):
    assert es.execution_blocked() is not None


def test_execution_blocked_is_none_when_clear():
    _reset()
    assert es.execution_blocked() is None


def test_execution_blocked_survives_a_broken_store():
    """A store failure must not take the caller down."""
    es.set_emergency_stop(object())
    assert es.execution_blocked() is None
    _reset()


def test_engine_gate_shares_the_same_decision(stopped):
    from app.core.agent_engine import _emergency_stop_active

    assert _emergency_stop_active() is True


async def test_workflow_engine_refuses_while_stopped(stopped):
    from app.workflow.engine import WorkflowEngine

    class _Workflow:
        id = "wf-1"

    engine = WorkflowEngine(engine=None)
    result = await engine.execute(_Workflow())

    assert result.status == "emergency_stop"
    assert "Emergency stop" in result.error


async def test_crew_refuses_while_stopped(stopped):
    from app.multi_agent import AgentTask
    from app.multi_agent.crew import Crew

    task = AgentTask(
        id="t1", agent_name="a", description="do work", expected_output="a result"
    )
    crew = Crew(agents=[], tasks=[task], engine=None)

    output = await crew.execute()

    assert task.status == TaskStatus.FAILED
    assert "Emergency stop" in (task.error or "")
    assert "Emergency stop" in output.final_output


async def test_collaboration_refuses_while_stopped(stopped, monkeypatch):
    from app.core.collaboration import base as collab

    calls: list[tuple[str, str]] = []

    async def _fake_update(task_id: str, status: str) -> None:
        calls.append((task_id, status))

    monkeypatch.setattr(collab, "_update_task_status", _fake_update)

    engine = collab.GroupCollaborationEngine.__new__(collab.GroupCollaborationEngine)
    await engine.run_task("task-42")

    assert calls == [("task-42", "failed")]


async def test_run_group_tasks_refuses_while_stopped(stopped):
    from app.core.collaboration import base as collab

    engine = collab.GroupCollaborationEngine.__new__(collab.GroupCollaborationEngine)
    result = await engine.run_group_tasks("group-1")

    assert "Emergency stop" in result["error"]
    assert result["results"] == []


async def test_flow_executor_refuses_before_start_method(stopped):
    from app.multi_agent.flow import FlowExecutor, start

    calls: list[str] = []

    class _Flow:
        @start()
        async def begin(self, state):
            calls.append("started")

    executor = FlowExecutor(None, None, None)
    state = await executor.execute(_Flow())

    assert "Emergency stop" in state.errors["__emergency_stop__"]
    assert calls == []


async def test_named_flow_refuses_before_workflow_resolution(stopped, monkeypatch):
    from app.multi_agent.flow import Flow

    async def _unexpected_resolution(params):
        raise AssertionError("emergency stop must block workflow resolution")

    monkeypatch.setattr(Flow, "_resolve_workflow", _unexpected_resolution)
    result = await Flow(name="simple_qa").execute()

    assert result["status"] == "emergency_stop"
    assert "Emergency stop" in result["error"]


async def test_collaboration_agent_runner_refuses_before_engine_creation(stopped, monkeypatch):
    from app.core.collaboration import agent_runner

    class _ExplodingEngine:
        def __init__(self, **kwargs):
            raise AssertionError("emergency stop must block engine creation")

    monkeypatch.setattr(agent_runner, "AgentEngine", _ExplodingEngine)
    events = [
        event
        async for event in agent_runner.run_agent(
            "agent-1", "openai", "model-1", "", "system", "hello", []
        )
    ]

    assert len(events) == 1
    assert events[0].type.value == "error"
    assert "Emergency stop" in events[0].data["error"]


async def test_collaboration_retry_refuses_before_attempt(stopped, monkeypatch):
    from app.core.collaboration import agent_runner

    async def _unexpected_attempt(**kwargs):
        raise AssertionError("emergency stop must block retry attempts")

    monkeypatch.setattr(agent_runner, "run_agent_simple", _unexpected_attempt)
    result = await agent_runner.run_agent_with_retry(
        "agent-1", "openai", "model-1", "", "system", "hello", [], "group-1"
    )

    assert result == ("", 0)


async def test_paths_are_open_again_after_deactivation(stopped):
    stopped.deactivate(reason="clear", triggered_by="tester")
    assert es.execution_blocked() is None
