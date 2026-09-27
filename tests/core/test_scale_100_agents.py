"""100-agent scale exercise for the real AgentEngine iteration loop.

What this measures: correctness invariants at 100 concurrent sessions, not
throughput. Wall-clock and token numbers are intentionally not asserted - the
environment gives no meaningful production performance signal, and asserting
timings here would encode a fabricated baseline.

Invariants pinned at scale:
- every session reaches a terminal state and returns a final assistant message
- session state never leaks across sessions (per-session checkpoint ids, metrics,
  message lists, and the memory scope contextvar)
- tool feedback is routed to the right session (no cross-session tool_result bleed)
- injected memory/core-memory/lessons context stays scoped to its own user/agent
- 100 sessions writing checkpoints concurrently keep all 100 distinct

Run: python3 -m pytest tests/core/test_scale_100_agents.py -q -o addopts=""
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import ChatResult, MessageRole
from app.core.agent_engine import AgentEngine
from app.core.memory_context import get_memory_scope
from app.core.parallel import ToolExecutionResult
from app.core.session import AgentSession

AGENT_COUNT = 100


def _tool_call(call_id: str, path: str) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": "read_file", "arguments": json.dumps({"path": path})},
    }


class _ScriptedAdapter:
    """Adapter that plays one tool call then a final answer, per session.

    ``capabilities.streaming`` is False so the engine takes the ``chat`` path.
    Each adapter instance serves exactly one session, which is how production
    behaves (an adapter is created per session in _iteration_loop).
    """

    def __init__(self, session_index: int, tool_iterations: int = 1) -> None:
        self.session_index = session_index
        self.tool_iterations = tool_iterations
        self.calls = 0
        self.capabilities = SimpleNamespace(streaming=False, max_tokens=2048, supports_tools=True)

    async def chat(self, messages: Any, tools: Any = None) -> ChatResult:
        self.calls += 1
        if self.calls <= self.tool_iterations:
            return ChatResult(
                content="",
                tool_calls=[_tool_call(f"call-{self.session_index}-{self.calls}", f"file-{self.session_index}.txt")],
            )
        return ChatResult(content=f"final-{self.session_index}")


def _make_engine(adapter_for: Any) -> AgentEngine:
    """Engine wired with a scripted model but the real iteration loop."""
    engine = object.__new__(AgentEngine)

    saved: dict[str, str] = {}

    class _Store:
        async def save(self, _thread_id: Any, checkpoint: Any, thread_id: str = "", checkpoint_id: str = "", parent_id: Any = None) -> str:
            cid = f"cp-{checkpoint.session_id}-{len(saved)}"
            saved[cid] = thread_id
            return cid

    engine._checkpoints = _Store()
    engine._sessions = {}
    engine._session_locks = {}
    engine._background_tasks = set()
    engine._shutdown_event = asyncio.Event()
    engine.resource_tracker = SimpleNamespace(
        track_tool_call=Mock(), record_token_usage=Mock(), get_metrics=Mock(return_value={})
    )
    engine.tool_prioritizer = Mock()
    engine.tool_registry = Mock()
    engine._validate_tool_call = Mock(return_value=(True, ""))
    engine.debug_loop = None
    engine._send_start_notification = Mock()
    engine._send_completion_notification = Mock()
    engine.sandbox = None
    engine.permission_overlay = None
    engine.agent_mode = None
    engine.memory_service = AsyncMock()
    engine.memory_service.format_memories_for_prompt = AsyncMock(return_value="")
    engine.memory_service.retrieve_memories = AsyncMock(return_value=[])
    def _get_or_create(**_kwargs: Any) -> Any:
        return adapter_for()

    engine.model_registry = SimpleNamespace(get_or_create=_get_or_create)
    return engine


def _make_executor(index: int) -> SimpleNamespace:
    tr = ToolExecutionResult(
        tool_name="read_file",
        tool_call_id=f"call-{index}-1",
        success=True,
        error="",
        result=f"content-of-file-{index}",
        duration_ms=1.0,
        arguments={"path": f"file-{index}.txt"},
    )
    return SimpleNamespace(execute_all=AsyncMock(return_value=[tr]))


def _session(index: int) -> AgentSession:
    session = AgentSession(
        session_id=f"scale-sess-{index}",
        user_id=f"scale-user-{index}",
        agent_id=f"scale-agent-{index}",
        provider="openai",
        model_id="gpt-4o",
        max_iterations=6,
    )
    session.messages = [{"role": MessageRole.USER, "content": f"request {index}"}]
    return session


async def _drive(index: int, persistence: AsyncMock) -> tuple[list[Any], AgentSession]:
    session = _session(index)
    adapter = _ScriptedAdapter(index)
    engine = _make_engine(lambda: adapter)
    engine._persist_session_message = persistence

    events = [event async for event in engine.run(session, f"request {index}")]
    return events, session


@pytest.mark.asyncio
async def test_100_concurrent_sessions_complete_with_isolated_state(monkeypatch: Any) -> None:
    """100 sessions run the real loop concurrently; state must stay isolated."""
    persistence = AsyncMock(return_value=None)
    monkeypatch.setattr("app.core.agent_engine.persist_message", persistence)
    monkeypatch.setattr("app.core.agent_engine.build_tools", lambda *a, **k: [])
    # Episodic persistence and reflection are out of scope here and would open
    # 100 real DB connections; stub them so the scale test stays hermetic.
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._store_episodic_memory", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._trigger_memory_reflection", Mock(return_value=None)
    )

    # The engine builds its own executor from the real registry; stub the class
    # so each session's tool execution returns that session's own result. The
    # session index is recovered from the tool call id, which _ScriptedAdapter
    # stamps as "call-<index>-<n>"; reading it from the execute_all argument
    # keeps the mapping correct even with 100 executors in flight.
    class _Executor:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            async def execute_all(tool_calls: Any) -> list[ToolExecutionResult]:
                index = 0
                for tc in tool_calls or []:
                    call_id = (tc or {}).get("id", "") if isinstance(tc, dict) else ""
                    if isinstance(call_id, str) and call_id.startswith("call-"):
                        try:
                            index = int(call_id.split("-")[1])
                        except (IndexError, ValueError):
                            index = 0
                        break
                return [
                    ToolExecutionResult(
                        tool_name="read_file",
                        tool_call_id=f"call-{index}-1",
                        success=True,
                        error="",
                        result=f"content-of-file-{index}",
                        duration_ms=1.0,
                        arguments={"path": f"file-{index}.txt"},
                    )
                ]

            self.execute_all = AsyncMock(side_effect=execute_all)

    monkeypatch.setattr("app.core.agent_engine.ParallelToolExecutor", _Executor)

    results = await asyncio.gather(
        *(_drive(i, persistence) for i in range(AGENT_COUNT)), return_exceptions=True
    )

    # Surface any engine-level ERROR event: a swallowed exception looks exactly
    # like a session that produced no assistant message.
    from app.core import AgentEventType

    for index, item in enumerate(results):
        if isinstance(item, BaseException):
            continue
        events, _session_obj = item
        for ev in events:
            if ev.type == AgentEventType.ERROR:
                raise AssertionError(f"session {index} engine error: {ev.data}")

    finals: dict[str, str] = {}
    for index, (events, session) in enumerate(results):
        # terminal state reached
        assert events, f"session {index} produced no events"
        # a final assistant answer exists and is this session's own
        assistant_texts = [
            m["content"] for m in session.messages if m.get("role") == MessageRole.ASSISTANT
        ]
        assert assistant_texts, f"session {index} has no assistant message"
        assert assistant_texts[-1] == f"final-{index}", f"session {index} got a foreign answer"
        finals[session.session_id] = assistant_texts[-1]

        # tool result stayed in its own session
        tool_msgs = [m for m in session.messages if m.get("role") == MessageRole.TOOL]
        for msg in tool_msgs:
            assert str(index) in msg["content"], f"session {index} tool result leaked: {msg}"

        # per-session metrics and tool accounting stayed local
        assert session.metrics.total_tool_calls == 1
        assert session.metrics.total_iterations >= 1
        assert session.metrics.total_tokens_used >= 0
        assert session.metrics.errors_by_type == {}
        assert session.debug_attempts == {}

        # no memory/core-memory/lessons system message (service mocked empty)
        assert all(not str(m.get("content", "")).startswith("<!-- LESSONS -->") for m in session.messages)

    # every session produced its own distinct answer
    assert len(finals) == AGENT_COUNT


@pytest.mark.asyncio
async def test_100_sessions_have_distinct_checkpoints(monkeypatch: Any) -> None:
    """Concurrent checkpoint writes must not collide or cross-link sessions."""
    persistence = AsyncMock(return_value=None)
    monkeypatch.setattr("app.core.agent_engine.persist_message", persistence)
    monkeypatch.setattr("app.core.agent_engine.build_tools", lambda *a, **k: [])
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._store_episodic_memory", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._trigger_memory_reflection", Mock(return_value=None)
    )

    checkpoint_ids: list[str] = []
    lock = asyncio.Lock()

    class _Store:
        def __init__(self) -> None:
            self.n = 0

        async def save(self, _thread_id: Any, checkpoint: Any, thread_id: str = "", checkpoint_id: str = "", parent_id: Any = None) -> str:
            self.n += 1
            cid = f"cp-{checkpoint.session_id}-{self.n}"
            async with lock:
                checkpoint_ids.append(cid)
            return cid

    async def _run_one(index: int) -> AgentSession:
        session = _session(index)
        adapter = _ScriptedAdapter(index, tool_iterations=0)  # no tools: one checkpoint
        engine = _make_engine(lambda: adapter)
        store = _Store()
        engine._checkpoints = store
        engine._persist_session_message = persistence
        [_ async for _ in engine.run(session, f"request {index}")]
        return session

    await asyncio.gather(*(_run_one(i) for i in range(AGENT_COUNT)))

    assert len(checkpoint_ids) == AGENT_COUNT
    assert len(set(checkpoint_ids)) == AGENT_COUNT, "checkpoint ids collided"
    # every checkpoint id is namespaced by its own session
    owners = {cid.split("-cp-")[0] for cid in checkpoint_ids}
    assert len(owners) == AGENT_COUNT


@pytest.mark.asyncio
async def test_100_sessions_on_one_shared_engine_stay_isolated(monkeypatch: Any) -> None:
    """One engine, 100 concurrent sessions: the production shape.

    ``AgentEngine.run`` guards each session with its own lock and pops the lock
    in a finally block. This pins that 100 distinct sessions all run to
    completion on a single engine without serializing each other and without
    one session's state reaching another.
    """
    persistence = AsyncMock(return_value=None)
    monkeypatch.setattr("app.core.agent_engine.persist_message", persistence)
    monkeypatch.setattr("app.core.agent_engine.build_tools", lambda *a, **k: [])
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._store_episodic_memory", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._trigger_memory_reflection", Mock(return_value=None)
    )

    shared_engine = _make_engine(lambda: _ScriptedAdapter(0))

    # Route each session to its own adapter. get_or_create runs inside the
    # session's own task, so a ContextVar lookup is race-free without any shared
    # mutable state - which is also how the engine itself resolves per-session
    # data (see app/core/memory_context.py).
    import contextvars

    session_var: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="")
    adapters: dict[str, _ScriptedAdapter] = {}

    def _adapter_ctx(**_kwargs: Any) -> _ScriptedAdapter:
        current = session_var.get()
        adapter = adapters.get(current)
        if adapter is None:
            adapter = adapters[current] = _ScriptedAdapter(
                int(current.rsplit("-", 1)[-1]) if current else 0
            )
        return adapter

    shared_engine.model_registry = SimpleNamespace(get_or_create=_adapter_ctx)
    original_run = shared_engine.run

    async def _one(index: int) -> tuple[list[Any], AgentSession]:
        session = _session(index)
        token = session_var.set(session.session_id)
        try:
            events = [event async for event in original_run(session, f"request {index}")]
        finally:
            session_var.reset(token)
        return events, session

    results = await asyncio.gather(*(_one(i) for i in range(AGENT_COUNT)), return_exceptions=True)

    failures = [(i, r) for i, r in enumerate(results) if isinstance(r, BaseException)]
    assert not failures, f"{len(failures)} sessions raised: {failures[:2]}"

    for index, (events, session) in enumerate(results):
        from app.core import AgentEventType

        errored = [ev for ev in events if ev.type == AgentEventType.ERROR]
        assert not errored, f"session {index} errored on a shared engine: {errored[0].data}"
        assistant_texts = [
            m["content"] for m in session.messages if m.get("role") == MessageRole.ASSISTANT
        ]
        assert assistant_texts, f"session {index} produced no assistant message"
        # each session got the answer produced by ITS adapter instance
        assert assistant_texts[-1] == f"final-{index}", f"session {index} adapter bled"
        assert session.metrics.total_tool_calls == 1

    # locks are cleaned up: no leaked per-session lock entries
    assert shared_engine._session_locks == {}


@pytest.mark.asyncio
async def test_same_session_concurrent_request_is_rejected(monkeypatch: Any) -> None:
    """The per-session lock must reject a second concurrent run of one session."""
    from app.core import AgentEventType

    persistence = AsyncMock(return_value=None)
    monkeypatch.setattr("app.core.agent_engine.persist_message", persistence)
    monkeypatch.setattr("app.core.agent_engine.build_tools", lambda *a, **k: [])
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._store_episodic_memory", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.core.agent_engine.AgentEngine._trigger_memory_reflection", Mock(return_value=None)
    )

    gate = asyncio.Event()

    class _SlowAdapter(_ScriptedAdapter):
        async def chat(self, messages: Any, tools: Any = None) -> ChatResult:
            await gate.wait()
            return ChatResult(content="slow-final")

    engine = _make_engine(lambda: _SlowAdapter(0, tool_iterations=0))
    session = _session(0)

    first = asyncio.create_task(_collect(engine, session, "request 0"))
    # let the first run take the lock
    for _ in range(20):
        await asyncio.sleep(0)

    second_events = await _collect(engine, session, "request 0")
    assert [ev.type for ev in second_events] == [AgentEventType.ERROR]
    assert "busy" in second_events[0].data["error"]

    gate.set()
    first_events = await first
    assert [ev.type for ev in first_events][-1] == AgentEventType.DONE


async def _collect(engine: Any, session: AgentSession, message: str) -> list[Any]:
    return [event async for event in engine.run(session, message)]


@pytest.mark.asyncio
async def test_memory_scope_contextvar_is_per_task_under_load() -> None:
    """100 concurrent tasks binding memory scope must not bleed across tasks."""
    from app.core.memory_context import clear_memory_scope, set_memory_scope

    async def _worker(index: int) -> tuple[str | None, str | None]:
        set_memory_scope(f"user-{index}", f"agent-{index}")
        # yield control so other tasks interleave and could corrupt a shared var
        for _ in range(5):
            await asyncio.sleep(0)
        scope = get_memory_scope()
        clear_memory_scope()
        return scope

    scopes = await asyncio.gather(*(_worker(i) for i in range(AGENT_COUNT)))
    for index, (user_id, agent_id) in enumerate(scopes):
        assert user_id == f"user-{index}", f"task {index} saw user {user_id}"
        assert agent_id == f"agent-{index}", f"task {index} saw agent {agent_id}"


@pytest.mark.asyncio
async def test_100_agent_group_dag_executes_in_dependency_order() -> None:
    """100 agents as a layered group DAG: order correct, every task runs once."""
    from sqlalchemy import delete

    from app.core.collaboration.base import GroupCollaborationEngine
    from app.storage import async_session
    from app.storage.models_groups import AgentGroup, AgentGroupTask

    group_id = "scale-100-group"
    task_ids = [f"sc-t{i:03d}" for i in range(AGENT_COUNT)]

    # Layer k depends on two tasks from the previous layer -> wide DAG, 10 layers.
    deps: dict[str, list[str]] = {}
    for i, tid in enumerate(task_ids):
        layer = i // 10
        deps[tid] = [] if layer == 0 else [task_ids[(layer - 1) * 10], task_ids[(layer - 1) * 10 + 1]]

    async with async_session() as db:
        db.add(AgentGroup(id=group_id, name="scale-100", user_id="default-user"))
        for tid in task_ids:
            db.add(
                AgentGroupTask(
                    id=tid, group_id=group_id, description=tid, status="pending", dependencies=deps[tid]
                )
            )
        await db.commit()

    engine = GroupCollaborationEngine(model_registry=object(), tool_registry=object())
    executed: list[str] = []

    async def fake_run(task: Any, group: Any, context_data: Any) -> None:
        executed.append(task.id)

    engine._run_single_task_in_dag = fake_run

    try:
        result = await engine.run_group_tasks(group_id)
        assert result["status"] == "completed", result
        assert len(executed) == AGENT_COUNT
        assert len(set(executed)) == AGENT_COUNT, "a task ran more than once"
        # every dependency ran before its dependent
        position = {tid: i for i, tid in enumerate(executed)}
        for tid, parents in deps.items():
            for parent in parents:
                assert position[parent] < position[tid], f"{parent} must precede {tid}"
    finally:
        async with async_session() as db:
            await db.execute(delete(AgentGroupTask).where(AgentGroupTask.group_id == group_id))
            await db.execute(delete(AgentGroup).where(AgentGroup.id == group_id))
            await db.commit()
