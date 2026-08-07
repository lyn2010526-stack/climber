from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.engine.validation import validate_tool_call
from app.core.executor import CrewExecutorAdapter
from app.core.interfaces import ExecutionContext, ExecutionStatus
from app.core.permission_rules import PermissionConfig, PermissionMode
from app.core.security_sandbox import PermissionLevel, PermissionOverlay, PermissionRule
from app.engine.multi_agent import MultiAgentOrchestrator
from app.multi_agent import CrewOutput


class ProtocolEngine:
    def __init__(self) -> None:
        self.agent_ids: list[str] = []

    def create_session(self, **kwargs):
        self.agent_ids.append(kwargs["agent_id"])
        return SimpleNamespace(**kwargs)

    async def run(self, session, message):
        yield AgentEvent(AgentEventType.TEXT, {"content": f"{session.agent_id}:{message}"})


@pytest.mark.asyncio
async def test_orchestrator_uses_sync_create_session_event_enum_and_roles():
    engine = ProtocolEngine()
    result = await MultiAgentOrchestrator(engine).team("ship", ["lead", "builder", "auditor"])

    assert result["success"] is True
    assert engine.agent_ids == ["lead", "builder", "auditor"]
    assert result["output"].startswith("builder:")


@pytest.mark.asyncio
async def test_run_agent_aggregates_stream_output_and_tokens():
    engine = object.__new__(AgentEngine)

    async def run(session, message):
        yield AgentEvent(AgentEventType.TEXT, {"content": "part-1"})
        yield AgentEvent(AgentEventType.TEXT, {"content": "-part-2"})
        yield AgentEvent(AgentEventType.DONE, {"tokens_used": 17})

    engine.run = run
    result = await engine.run_agent(SimpleNamespace(), "task")

    assert result == {"output": "part-1-part-2", "tokens_used": 17}


def test_permission_overlay_specificity_and_user_deny_win():
    overlay = PermissionOverlay()
    overlay.set_defaults([PermissionRule("write", "*", PermissionLevel.ALLOW)])
    overlay.set_user_rules("u1", [
        PermissionRule("write", "*", PermissionLevel.ALLOW),
        PermissionRule("write", "/private/*", PermissionLevel.DENY),
    ])

    assert overlay.evaluate("write", "/private/key", user_id="u1") == PermissionLevel.DENY


def test_validation_returns_structured_approval_request():
    session = SimpleNamespace(
        permission_config=PermissionConfig(mode=PermissionMode.DEFAULT),
        agent_id="a1",
        user_id="u1",
    )
    allowed, reason = validate_tool_call(session, "write_file", {"path": "note.txt"})

    assert allowed is False
    assert reason["requires_approval"] is True
    assert reason["tool_name"] == "write_file"


@pytest.mark.asyncio
async def test_agent_engine_permission_resolve_and_timeout_fail_closed(monkeypatch):
    monkeypatch.setattr("app.core.agent_engine.persist_message", _async_none)
    engine = object.__new__(AgentEngine)
    engine.permission_timeout_seconds = 0.03
    engine.tool_prioritizer = SimpleNamespace(record_outcome=lambda *args: None)
    engine.debug_loop = None
    engine._sessions = {}
    engine._checkpoints = SimpleNamespace(save=_async_none)
    engine.tool_registry = SimpleNamespace(get_tool=lambda name: None)
    engine.sandbox = None
    engine.permission_overlay = None
    engine.agent_mode = None
    session = SimpleNamespace(
        session_id="s1",
        agent_id="a1",
        user_id="u1",
        permission_config=PermissionConfig(mode=PermissionMode.DEFAULT),
        messages=[],
        metrics=SimpleNamespace(total_tool_calls=0, tool_call_durations=[]),
        _pending_permission=None,
        _permission_event=None,
        state_machine=SimpleNamespace(state=SimpleNamespace(value="processing")),
    )
    engine._sessions[session.session_id] = session
    result = SimpleNamespace(tool_calls=[{
        "id": "call-1",
        "function": {"name": "write_file", "arguments": {"path": "note.txt"}},
    }])

    resolving_executor = RecordingExecutor(engine, session)
    consume_task = asyncio.create_task(_consume_tool_execution(engine, session, resolving_executor, result, 1))
    await _wait_for_pending_permission(session)
    assert engine.resolve_permission("call-1", "allow") is True
    events = await consume_task
    approval = next(event for event in events if event.data.get("requires_approval"))
    assert approval.data["tool_call_id"] == "call-1"
    assert resolving_executor.executed is True

    session._approved_tool_calls = set()
    timeout_executor = RecordingExecutor(engine, session)
    events = [event async for event in engine._handle_tool_execution(session, timeout_executor, result, 2, 0)]
    assert timeout_executor.executed is False
    assert any(event.type == AgentEventType.TOOL_RESULT for event in events)


async def _async_none(*args, **kwargs):
    return None


class RecordingExecutor:
    def __init__(self, engine: AgentEngine, session) -> None:
        self.engine = engine
        self.session = session
        self.executed = False

    async def execute_all(self, tool_calls):
        function = tool_calls[0]["function"]
        allowed, reason = self.engine._validate_tool_call(
            self.session,
            function["name"],
            function["arguments"],
        )
        self.executed = allowed
        return [SimpleNamespace(
            tool_name="write_file",
            success=allowed,
            duration_ms=0.0,
            result="written" if allowed else "",
            error="" if allowed else str(reason),
            tool_call_id="call-1",
            arguments={"path": "note.txt"},
        )]


async def _consume_tool_execution(engine, session, executor, result, iteration):
    return [
        event
        async for event in engine._handle_tool_execution(session, executor, result, iteration, 0)
    ]


async def _wait_for_pending_permission(session):
    for _ in range(20):
        if session._pending_permission is not None:
            return
        await asyncio.sleep(0)
    raise AssertionError("permission request was not created")


@pytest.mark.asyncio
async def test_crew_adapter_converts_crew_output():
    output = CrewOutput(
        crew_id="crew-1",
        results=[{"result": "done"}],
        final_output="done",
        total_iterations=1,
    )
    crew = SimpleNamespace(execute=lambda **kwargs: _return(output))
    result = await CrewExecutorAdapter(crew).execute(ExecutionContext("s1", "u1"))

    assert result.status == ExecutionStatus.COMPLETED
    assert result.output == "done"
    assert result.metrics["crew_id"] == "crew-1"


async def _return(value):
    return value


def test_builtins_resolves_group_engine_for_each_call(monkeypatch):
    from app.core import group_collaboration
    from app.tools import builtins

    engines = [object(), object()]
    monkeypatch.setattr(group_collaboration, "get_group_collaboration_engine", lambda: engines.pop(0))

    assert builtins._get_group_engine() is not builtins._get_group_engine()
