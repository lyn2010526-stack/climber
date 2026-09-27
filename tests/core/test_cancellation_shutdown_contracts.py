"""Regression coverage for cancellation, timeout, shutdown, and stop paths.

These tests deliberately use events instead of elapsed-time sleeps.  Each
cancelled child is awaited or explicitly drained so a failure cannot leak a
task into the next test.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.resilience import RetryExhaustedError, TimeoutConfig
from app.core.session import AgentSession, SessionConfig
from app.multi_agent import AgentRole, AgentTask, TaskStatus
from app.multi_agent.crew import Crew
from app.multi_agent.flow import FlowExecutor, start
from app.workflow import NodeType, Workflow, WorkflowNode
from app.workflow.engine import WorkflowEngine


def _session(session_id: str = "test-session") -> AgentSession:
    return AgentSession(session_id=session_id, agent_id="agent", user_id="user")


def _engine_without_init() -> AgentEngine:
    engine = AgentEngine.__new__(AgentEngine)
    engine.tool_registry = None
    engine.tool_prioritizer = None
    return engine


@pytest.mark.asyncio
async def test_agent_engine_timeout_is_reported_as_retry_exhaustion(monkeypatch) -> None:
    engine = _engine_without_init()
    session = AgentSession(
        SessionConfig(
            session_id="timeout-session",
            timeouts=TimeoutConfig(per_call_seconds=0.001),
        )
    )

    async def _never_returns(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr("app.core.agent_engine.build_tools", lambda *args, **kwargs: [])
    adapter = SimpleNamespace(
        capabilities=SimpleNamespace(streaming=False),
        chat=_never_returns,
    )

    with pytest.raises(RetryExhaustedError, match="timed out"):
        await engine._call_llm_with_resilience(session, adapter, [], iteration=1)

    assert session.metrics.retry_count == 1
    assert session.metrics.llm_call_durations


@pytest.mark.asyncio
async def test_workflow_cancellation_does_not_leave_node_running() -> None:
    node = WorkflowNode(id="llm", type=NodeType.LLM, name="blocked")
    workflow = Workflow(
        id="workflow-1",
        name="cancellation",
        nodes=[
            WorkflowNode(id="start", type=NodeType.START, name="start"),
            node,
        ],
        edges=[],
    )
    started = asyncio.Event()
    child_task: asyncio.Task | None = None

    async def _blocked_llm(*args, **kwargs) -> None:
        nonlocal child_task
        child_task = asyncio.current_task()
        started.set()
        await asyncio.Event().wait()

    executor = WorkflowEngine(engine=None)
    executor._execute_llm_node = _blocked_llm
    task = asyncio.create_task(executor.execute(workflow))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert node.status != "running"
    assert child_task is not None
    assert child_task.done()


@pytest.mark.asyncio
async def test_flow_executor_cancellation_drains_started_methods() -> None:
    started = asyncio.Event()
    finished = asyncio.Event()
    child_task: asyncio.Task | None = None

    class _Flow:
        @start()
        async def begin(self, state):
            nonlocal child_task
            child_task = asyncio.current_task()
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

    executor = FlowExecutor(None, None, None)
    task = asyncio.create_task(executor.execute(_Flow()))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert child_task is not None
    try:
        assert child_task.done()
        assert finished.is_set()
    finally:
        if not child_task.done():
            child_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await child_task


@pytest.mark.asyncio
async def test_parallel_crew_cancellation_does_not_leave_tasks_running() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    child_tasks: list[asyncio.Task] = []

    class _BlockingEngine:
        def create_session(self, **kwargs):
            return "session"

        async def run(self, session, message):
            child_tasks.append(asyncio.current_task())
            started.set()
            try:
                await release.wait()
            finally:
                yield AgentEvent(type=AgentEventType.DONE, data={})

    agent = AgentRole(name="alpha", role="role", goal="goal", backstory="story")
    tasks = [
        AgentTask(id="one", agent_name="alpha", description="one", expected_output="one"),
        AgentTask(id="two", agent_name="alpha", description="two", expected_output="two"),
    ]
    crew = Crew([agent], tasks, _BlockingEngine(), process="parallel")
    execution = asyncio.create_task(crew.execute())
    await started.wait()
    execution.cancel()

    with pytest.raises(asyncio.CancelledError):
        await execution

    try:
        assert all(task.status != TaskStatus.RUNNING for task in tasks)
    finally:
        for child_task in child_tasks:
            if not child_task.done():
                child_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await child_task


@pytest.mark.asyncio
async def test_engine_shutdown_marks_active_session_for_stop() -> None:
    engine = AgentEngine.__new__(AgentEngine)
    session = _session("shutdown-session")
    engine._sessions = {session.session_id: session}
    engine._background_tasks = set()
    engine._shutdown_event = asyncio.Event()
    engine.resource_tracker = SimpleNamespace(cleanup=lambda: asyncio.sleep(0))

    await engine.graceful_shutdown()

    assert engine._shutdown_event.is_set()
    assert session._stop_requested is True
    assert session.metrics.end_time is not None
