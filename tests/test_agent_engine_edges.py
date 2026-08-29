"""Edge/error-path tests for the agent engine ReAct loop.

Covers the paths the happy-path tests in test_agent_engine.py miss:
model/stream failure, tool execution failure, approval interception,
max-iteration boundary, context compression on long input, empty input,
session restart and permission resolution. All model/tool IO is mocked.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio

from app.core import AgentEventType, ChatResult, ContextConfig, SessionStatus
from app.core.agent_engine import AgentEngine
from app.core.checkpoint import InMemoryCheckpointStore
from app.core.task_state_machine import TaskState
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry
from tests.test_agent_engine import FakeModelAdapter, StreamingFakeModelAdapter


class _FailingModel(FakeModelAdapter):
    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, **kwargs: Any) -> ChatResult:
        raise RuntimeError("model exploded")


class _FailingStream(StreamingFakeModelAdapter):
    async def stream_chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None, **kwargs: Any) -> Any:
        raise RuntimeError("stream exploded")
        yield ChatResult(content="")  # pragma: no cover - make this an async generator


class _FakeMemory:
    async def format_memories_for_prompt(self, user_id: str, query: str, max_memories: int = 5) -> str:
        return ""

    async def create_episodic_memory(self, **kwargs: Any) -> None:
        return None


async def _noop_persist(*args: Any, **kwargs: Any) -> None:
    return None


class _RecordingCheckpointStore(InMemoryCheckpointStore):
    def __init__(self) -> None:
        super().__init__()
        self.saves: list[tuple[str, str]] = []

    async def save(
        self,
        _thread_id: str | None,
        checkpoint: Any,
        thread_id: str = "",
        checkpoint_id: str = "",
        parent_id: str | None = None,
    ) -> str:
        self.saves.append((thread_id, checkpoint_id))
        return await super().save(
            _thread_id,
            checkpoint,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            parent_id=parent_id,
        )


@pytest_asyncio.fixture
async def engine():
    from app.core.permission_rules import PermissionConfig, PermissionMode

    model_registry = ModelRegistry()
    tool_registry = ToolRegistry()

    @tool_registry.tool(
        name="echo",
        description="Echo back the input",
        sandbox_safe_when_unavailable=True,
    )
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    @tool_registry.tool(
        name="boom",
        description="Always fails",
        sandbox_safe_when_unavailable=True,
    )
    async def boom(text: str) -> str:
        raise RuntimeError("tool crashed")

    @tool_registry.tool(name="write_file", description="Write a file")
    async def write_file(path: str, content: str) -> str:
        return f"wrote {path}: {content}"

    @tool_registry.tool(
        name="read_file",
        description="Read a file",
        sandbox_safe_when_unavailable=True,
    )
    async def read_file(path: str) -> str:
        return f"read {path}"

    engine = AgentEngine(model_registry=model_registry, tool_registry=tool_registry)
    engine._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)
    engine.debug_loop = None
    engine.memory_service = _FakeMemory()
    engine._persist_message = _noop_persist
    return engine


def _register(engine: AgentEngine, adapter: Any) -> None:
    engine.model_registry._models["fake:fake-model"] = adapter


def _session(engine: AgentEngine, **kw: Any) -> Any:
    return engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
        **kw,
    )


async def _collect(engine: AgentEngine, session: Any, message: str) -> list:
    return [event async for event in engine.run(session, message)]


@pytest.mark.asyncio
async def test_empty_message_completes(engine: AgentEngine):
    _register(engine, FakeModelAdapter(responses=[ChatResult(content="ok", finish_reason="stop")]))
    session = _session(engine)
    events = await _collect(engine, session, "")
    assert events[-1].type == AgentEventType.DONE
    assert session.status == SessionStatus.COMPLETED
    user_msgs = [m for m in session.messages if m.get("role") == "user"]
    assert user_msgs and user_msgs[-1]["content"] == ""


@pytest.mark.asyncio
async def test_each_run_uses_a_distinct_turn_for_checkpoints(engine: AgentEngine):
    _register(
        engine,
        FakeModelAdapter(
            responses=[
                ChatResult(content="first", finish_reason="stop"),
                ChatResult(content="second", finish_reason="stop"),
            ]
        ),
    )
    store = _RecordingCheckpointStore()
    engine._checkpoints = store
    session = _session(engine)

    await _collect(engine, session, "first turn")
    first_turn_id = session.current_turn_id
    await _collect(engine, session, "second turn")
    second_turn_id = session.current_turn_id

    assert first_turn_id
    assert second_turn_id
    assert first_turn_id != second_turn_id
    assert [thread_id for thread_id, _ in store.saves] == [
        first_turn_id,
        second_turn_id,
    ]
    checkpoint_ids = [checkpoint_id for _, checkpoint_id in store.saves]
    assert checkpoint_ids[0] != checkpoint_ids[1]
    assert all(len(checkpoint_id) == 36 for checkpoint_id in checkpoint_ids)


@pytest.mark.asyncio
async def test_run_retains_events_for_replay(engine: AgentEngine):
    _register(engine, FakeModelAdapter(responses=[ChatResult(content="replay me", finish_reason="stop")]))
    session = _session(engine)

    await _collect(engine, session, "record this")
    replayed = engine.replay_events(session)

    assert [event.event_type for event in replayed] == [
        "thinking",
        "text",
        "checkpoint",
        "done",
    ]
    assert all(replayed[index].sequence < replayed[index + 1].sequence for index in range(len(replayed) - 1))
    assert {event.turn_id for event in replayed} == {session.current_turn_id}


@pytest.mark.asyncio
async def test_replay_can_isolate_one_turn_after_multiple_runs(engine: AgentEngine):
    _register(
        engine,
        FakeModelAdapter(
            responses=[
                ChatResult(content="first", finish_reason="stop"),
                ChatResult(content="second", finish_reason="stop"),
            ]
        ),
    )
    session = _session(engine)

    await _collect(engine, session, "first")
    first_turn_id = session.current_turn_id
    await _collect(engine, session, "second")
    second_turn_id = session.current_turn_id

    assert first_turn_id != second_turn_id
    assert {event.turn_id for event in engine.replay_events(session, turn_id=first_turn_id)} == {first_turn_id}
    assert {event.turn_id for event in engine.replay_events(session, turn_id=second_turn_id)} == {second_turn_id}


@pytest.mark.asyncio
async def test_model_chat_failure_yields_error_and_fails(engine: AgentEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MODEL_RETRY_DELAY", "0")
    _register(engine, _FailingModel())
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    errors = [e for e in events if e.type == AgentEventType.ERROR]
    assert errors and "model exploded" in errors[0].data["error"]
    assert session.status == SessionStatus.FAILED


@pytest.mark.asyncio
async def test_stream_failure_yields_error_and_fails(engine: AgentEngine, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MODEL_RETRY_DELAY", "0")
    _register(engine, _FailingStream())
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    errors = [e for e in events if e.type == AgentEventType.ERROR]
    assert errors and "stream exploded" in errors[0].data["error"]
    assert session.status == SessionStatus.FAILED


@pytest.mark.asyncio
async def test_tool_execution_failure_is_graceful(engine: AgentEngine):
    tool_call = [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "boom", "arguments": {"text": "x"}},
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="recovered", finish_reason="stop"),
    ]))
    session = _session(engine, tools=["boom"])
    events = await _collect(engine, session, "do it")
    results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
    assert results and "tool crashed" in results[0].data["error"]
    assert results[0].data["id"] == "call_1"
    assert results[0].data["tool_call_id"] == "call_1"
    done = next(e for e in events if e.type == AgentEventType.DONE)
    assert "recovered" in done.data["content"]
    assert session.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_tool_result_event_reflects_successful_debug_recovery(engine: AgentEngine):
    class _SuccessfulDebugLoop:
        async def recover(self, **kwargs: Any) -> Any:
            return SimpleNamespace(success=True, output="recovered output")

    tool_call = [{
        "id": "call_recovered",
        "type": "function",
        "function": {"name": "boom", "arguments": {"text": "x"}},
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="finished", finish_reason="stop"),
    ]))
    engine.debug_loop = _SuccessfulDebugLoop()
    session = _session(engine, tools=["boom"])

    events = await _collect(engine, session, "do it")

    results = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
    assert len(results) == 1
    assert results[0].data == {
        "id": "call_recovered",
        "tool_call_id": "call_recovered",
        "tool_name": "boom",
        "result": "recovered output",
        "error": "",
    }
    tool_message = next(message for message in session.messages if message["role"] == "tool")
    assert tool_message["content"] == "recovered output"


@pytest.mark.asyncio
async def test_tool_loop_hits_max_iterations(engine: AgentEngine):
    tool_call = [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "echo", "arguments": {"text": "x"}},
    }]
    _register(engine, FakeModelAdapter(responses=[ChatResult(content="", tool_calls=tool_call)]))
    session = _session(engine, tools=["echo"])
    events = await _collect(engine, session, "loop")
    done = next(e for e in events if e.type == AgentEventType.DONE)
    assert done.data["status"] == "max_iterations_reached"
    assert session.status == SessionStatus.FAILED


@pytest.mark.asyncio
async def test_validate_tool_call_denies_and_allows(engine: AgentEngine):
    from app.core.permission_rules import PermissionConfig, PermissionMode, get_default_config

    session = _session(engine)
    allowed, reason = engine._validate_tool_call(session, "echo", {"text": "x"})
    assert allowed is True
    assert reason == "OK"

    session.permission_config = PermissionConfig(mode=PermissionMode.PLAN)
    denied, reason = engine._validate_tool_call(session, "echo", {"text": "x"})
    assert denied is False
    assert "denied" in reason.lower()

    session.permission_config = get_default_config()
    pending, reason = engine._validate_tool_call(
        session,
        "write_file",
        {"path": "/workspace/data/out.txt", "content": "hello"},
    )
    assert pending is True
    assert "approval" in reason.lower()

    invalid, reason = engine._validate_tool_call(
        session,
        "write_file",
        {"path": "/workspace/data/out.txt"},
    )
    assert invalid is False
    assert "content" in reason.lower()


def test_sandbox_unavailable_fails_closed_for_side_effecting_tools(engine: AgentEngine):
    from app.core.security_sandbox import PermissionLevel, PermissionOverlay, PermissionRule

    overlay = PermissionOverlay()
    overlay.set_defaults([
        PermissionRule(
            action="write",
            resource_pattern="*",
            level=PermissionLevel.ASK,
        ),
        PermissionRule(
            action="execute",
            resource_pattern="*",
            level=PermissionLevel.ALLOW,
        ),
    ])
    engine.permission_overlay = overlay
    engine.sandbox = None
    session = _session(engine)

    write_allowed, write_reason = engine._validate_tool_call(
        session,
        "write_file",
        {"path": "/workspace/data/out.txt", "content": "hello"},
    )
    command_allowed, command_reason = engine._validate_tool_call(
        session,
        "run_command",
        {"command": "pwd"},
    )

    assert write_allowed is False
    assert "sandbox unavailable" in write_reason.lower()
    assert command_allowed is False
    assert "sandbox unavailable" in command_reason.lower()


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("native_run", {"command": "pwd"}),
        ("stream_command", {"command": "pwd"}),
        ("container_exec", {"container": "worker", "command": "pwd"}),
        ("native_write_file", {"path": "/workspace/data/out.txt", "content": "hello"}),
        ("download_file", {"url": "https://example.com/file", "output_path": "/workspace/data/file"}),
    ],
)
def test_sandbox_unavailable_blocks_all_known_side_effecting_tool_aliases(
    engine: AgentEngine,
    tool_name: str,
    arguments: dict[str, Any],
):
    engine.sandbox = None
    session = _session(engine)

    allowed, reason = engine._validate_tool_call(session, tool_name, arguments)

    assert allowed is False
    assert "sandbox unavailable" in reason.lower()


def test_sandbox_unavailable_preserves_safe_tool_behavior(engine: AgentEngine):
    engine.sandbox = None
    session = _session(engine)

    echo_allowed, echo_reason = engine._validate_tool_call(session, "echo", {"text": "x"})
    read_allowed, read_reason = engine._validate_tool_call(
        session,
        "read_file",
        {"path": "/workspace/README.md"},
    )

    assert echo_allowed is True
    assert echo_reason == "OK"
    assert read_allowed is True
    assert read_reason == "OK"


def test_sandbox_unavailable_rejects_unclassified_dynamic_tool(engine: AgentEngine):
    @engine.tool_registry.tool(name="unclassified_tool", description="Unclassified dynamic tool")
    async def unclassified_tool() -> str:
        return "ran"

    engine.sandbox = None
    session = _session(engine)

    allowed, reason = engine._validate_tool_call(session, "unclassified_tool", {})

    assert allowed is False
    assert "sandbox unavailable" in reason.lower()


def test_mcp_tool_cannot_inherit_safe_read_behavior_by_name(engine: AgentEngine):
    class _MCPClient:
        name = "test-mcp"

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
            return "ran"

    engine.tool_registry.register_mcp_tool(
        name="read_file",
        description="MCP tool using a trusted-looking name",
        parameters={"type": "object", "properties": {}},
        mcp_client=_MCPClient(),
        mcp_tool_name="remote_read",
    )
    engine.sandbox = None
    session = _session(engine)

    allowed, reason = engine._validate_tool_call(session, "read_file", {})

    assert allowed is False
    assert "sandbox unavailable" in reason.lower()


@pytest.mark.asyncio
async def test_sandbox_rejection_cannot_execute_through_debug_recovery(engine: AgentEngine):
    class _RecordingDebugLoop:
        def __init__(self) -> None:
            self.calls = 0

        async def recover(self, **kwargs: Any) -> Any:
            self.calls += 1
            retry_callback = kwargs["retry_callback"]
            output = await retry_callback(kwargs["tool_name"], kwargs["arguments"])
            return SimpleNamespace(success=True, output=output)

    executions = 0

    @engine.tool_registry.tool(name="write_file", description="Record a write attempt")
    async def record_write(path: str, content: str) -> str:
        nonlocal executions
        executions += 1
        return "written"

    tool_call = [{
        "id": "call_blocked_write",
        "type": "function",
        "function": {
            "name": "write_file",
            "arguments": {"path": "/workspace/data/out.txt", "content": "hello"},
        },
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="finished", finish_reason="stop"),
    ]))
    debug_loop = _RecordingDebugLoop()
    engine.debug_loop = debug_loop
    engine.sandbox = None
    session = _session(engine, tools=["write_file"])

    events = await _collect(engine, session, "write it")

    tool_result = next(event for event in events if event.type == AgentEventType.TOOL_RESULT)
    assert "sandbox unavailable" in tool_result.data["error"].lower()
    assert executions == 0
    assert debug_loop.calls == 0


@pytest.mark.asyncio
async def test_debug_retry_cannot_switch_to_blocked_tool(engine: AgentEngine):
    class _SwitchingDebugLoop:
        def __init__(self) -> None:
            self.calls = 0

        async def recover(self, **kwargs: Any) -> Any:
            self.calls += 1
            output = await kwargs["retry_callback"](
                "write_file",
                {"path": "/workspace/data/out.txt", "content": "hello"},
            )
            return SimpleNamespace(
                success=not output.startswith("blocked by sandbox:"),
                output=output,
            )

    executions = 0

    @engine.tool_registry.tool(name="write_file", description="Record a write attempt")
    async def record_write(path: str, content: str) -> str:
        nonlocal executions
        executions += 1
        return "written"

    tool_call = [{
        "id": "call_failing_pure_tool",
        "type": "function",
        "function": {"name": "boom", "arguments": {"text": "x"}},
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="finished", finish_reason="stop"),
    ]))
    debug_loop = _SwitchingDebugLoop()
    engine.debug_loop = debug_loop
    engine.sandbox = None
    session = _session(engine, tools=["boom", "write_file"])

    events = await _collect(engine, session, "recover it")

    tool_result = next(event for event in events if event.type == AgentEventType.TOOL_RESULT)
    assert "tool crashed" in tool_result.data["error"]
    assert executions == 0
    assert debug_loop.calls == 1


@pytest.mark.asyncio
async def test_debug_retry_cannot_bypass_required_approval(engine: AgentEngine):
    from app.core.permission_rules import PermissionConfig, PermissionMode, PermissionRule, RuleDecision

    class _SwitchingDebugLoop:
        async def recover(self, **kwargs: Any) -> Any:
            output = await kwargs["retry_callback"](
                "write_file",
                {"path": "/workspace/data/out.txt", "content": "hello"},
            )
            return SimpleNamespace(success=True, output=output)

    executions = 0

    @engine.tool_registry.tool(name="write_file", description="Record a write attempt")
    async def record_write(path: str, content: str) -> str:
        nonlocal executions
        executions += 1
        return "written"

    tool_call = [{
        "id": "call_failing_pure_tool",
        "type": "function",
        "function": {"name": "boom", "arguments": {"text": "x"}},
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="finished", finish_reason="stop"),
    ]))
    engine.debug_loop = _SwitchingDebugLoop()
    session = _session(engine, tools=["boom", "write_file"])
    session.permission_config = PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "boom"),
            PermissionRule(RuleDecision.ASK, "write_file"),
        ],
    )

    events = await _collect(engine, session, "recover it")

    tool_result = next(event for event in events if event.type == AgentEventType.TOOL_RESULT)
    assert "tool crashed" in tool_result.data["error"]
    assert executions == 0


@pytest.mark.asyncio
async def test_permission_approval_pauses_then_resumes_tool_execution(
    engine: AgentEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    import app.core.approval as approval_module
    from app.core.approval import ApprovalManager
    from app.core.permission_rules import get_default_config

    manager = ApprovalManager()
    monkeypatch.setattr(approval_module, "approval_manager", manager)

    tool_call = [{
        "id": "call-write",
        "type": "function",
        "function": {
            "name": "write_file",
            "arguments": {"path": "/workspace/data/out.txt", "content": "hello"},
        },
    }]
    _register(engine, FakeModelAdapter(responses=[
        ChatResult(content="", tool_calls=tool_call),
        ChatResult(content="finished", finish_reason="stop"),
    ]))
    session = _session(engine, tools=["write_file"])
    session.permission_config = get_default_config()

    run_task = asyncio.create_task(_collect(engine, session, "write it"))
    for _ in range(100):
        pending = manager.get_pending(session_id=session.session_id)
        if pending:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError("approval request was not created")

    assert run_task.done() is False
    assert pending[0].tool_name == "write_file"
    assert session.state_machine.state == TaskState.PAUSED
    await manager.approve_async(pending[0].id)

    events = await asyncio.wait_for(run_task, timeout=2)
    tool_result = next(e for e in events if e.type == AgentEventType.TOOL_RESULT)
    assert tool_result.data["result"] == "wrote /workspace/data/out.txt: hello"
    assert events[-1].type == AgentEventType.DONE
    assert session.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_resolve_permission_pending_and_missing(engine: AgentEngine):
    from app.core.approval import approval_manager

    assert await engine.resolve_permission_async("call-missing", "allow") is False

    req = await approval_manager.request(
        session_id="test-session", tool_name="write_file", arguments={"path": "/tmp/x"}
    )
    assert await engine.resolve_permission_async(req.id, "allow") is True
    assert await engine.resolve_permission_async(req.id, "allow") is False  # already resolved


@pytest.mark.asyncio
async def test_resolve_permission_rejects_request_owned_by_another_user(engine: AgentEngine):
    from app.core.approval import approval_manager

    req = await approval_manager.request(
        session_id="other-session",
        tool_name="write_file",
        arguments={"path": "/tmp/x"},
        user_id="other-user",
    )

    assert await engine.resolve_permission_async(req.id, "allow", user_id="current-user") is False
    stored = await approval_manager.get_request_async(req.id)
    assert stored is not None
    assert stored.status == "pending"


@pytest.mark.asyncio
async def test_resolve_permission_async_uses_durable_store_across_instances(
    engine: AgentEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    import app.core.approval as approval_module
    from app.core.approval import ApprovalManager

    creator = ApprovalManager()
    resolver = ApprovalManager()
    monkeypatch.setattr(approval_module, "approval_manager", resolver)
    request = await creator.request("shared-session", "write_file", {"path": "/tmp/x"})

    resolved = await engine.resolve_permission_async(request.id, "allow")
    stored = await creator.get_request_async(request.id)

    assert resolved is True
    assert stored is not None
    assert stored.status == "approved"


@pytest.mark.asyncio
async def test_stop_flushes_buffered_messages(engine: AgentEngine, monkeypatch):
    flushed = []
    engine._msg_buffers["session-1"] = [{"role": "user", "content": "pending"}]

    async def fake_flush(session_id: str):
        flushed.append(session_id)

    monkeypatch.setattr(engine, "_flush_buffer", fake_flush)
    engine.start()
    flush_task = engine._flush_task
    assert flush_task is not None
    await engine.stop()

    assert flushed == ["session-1"]
    assert flush_task.cancelled()


@pytest.mark.asyncio
async def test_context_compression_on_long_input(engine: AgentEngine):
    _register(engine, FakeModelAdapter(responses=[ChatResult(content="short", finish_reason="stop")]))
    session = _session(engine, context_config=ContextConfig(max_tokens=50))
    events = await _collect(engine, session, "a" * 1000)
    assert any(e.type == AgentEventType.CONTEXT_COMPRESSION for e in events)
    assert events[-1].type == AgentEventType.DONE


class _RetryThenSucceedStream(StreamingFakeModelAdapter):
    def __init__(self, failures: int = 1):
        super().__init__(responses=[ChatResult(content="recovered", finish_reason="stop")], stream_chunks=[["recovered"]])
        self._failures_remaining = failures
        self._call_count = 0

    async def stream_chat(self, messages, tools=None, **kwargs):
        self._call_count += 1
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            raise RuntimeError("transient stream failure")
        async for c in super().stream_chat(messages, tools=tools, **kwargs):
            yield c


class _RetryThenSucceedChat(FakeModelAdapter):
    def __init__(self, failures: int = 1):
        super().__init__(responses=[ChatResult(content="recovered", finish_reason="stop")])
        self._failures_remaining = failures

    async def chat(self, messages, tools=None, **kwargs):
        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            raise RuntimeError("transient chat failure")
        return ChatResult(content="recovered", finish_reason="stop")


@pytest.mark.asyncio
async def test_stream_transient_failure_retries_and_succeeds(engine: AgentEngine, monkeypatch):
    monkeypatch.setenv("MODEL_MAX_RETRIES", "3")
    monkeypatch.setenv("MODEL_RETRY_DELAY", "0")
    adapter = _RetryThenSucceedStream(failures=2)
    _register(engine, adapter)
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    assert events[-1].type == AgentEventType.DONE
    assert session.status == SessionStatus.COMPLETED
    text = "".join(e.data.get("content", "") for e in events if e.type == AgentEventType.TEXT)
    assert "recovered" in text
    assert adapter._failures_remaining == 0


@pytest.mark.asyncio
async def test_chat_transient_failure_retries_and_succeeds(engine: AgentEngine, monkeypatch):
    monkeypatch.setenv("MODEL_MAX_RETRIES", "3")
    monkeypatch.setenv("MODEL_RETRY_DELAY", "0")
    adapter = _RetryThenSucceedChat(failures=2)
    _register(engine, adapter)
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    assert events[-1].type == AgentEventType.DONE
    assert session.status == SessionStatus.COMPLETED
    text = "".join(e.data.get("content", "") for e in events if e.type == AgentEventType.TEXT)
    assert text == "recovered"


@pytest.mark.asyncio
async def test_stream_empty_result_retries(engine: AgentEngine, monkeypatch):
    monkeypatch.setenv("MODEL_MAX_RETRIES", "2")
    monkeypatch.setenv("MODEL_RETRY_DELAY", "0")
    calls = {"n": 0}

    class _EmptyThenOk(StreamingFakeModelAdapter):
        async def stream_chat(self, messages, tools=None, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return
            yield ChatResult(content="ok", tool_calls=[], finish_reason="stop")

    adapter = _EmptyThenOk(responses=[ChatResult(content="ok", finish_reason="stop")], stream_chunks=[["ok"]])
    _register(engine, adapter)
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    assert events[-1].type == AgentEventType.DONE
    assert calls["n"] == 2
