"""Contract tests for tool feedback; run with --noconftest and asyncio.run.

The scripted adapter checks information flow only, not model performance.
"""

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

from app.core import AgentEventType, ChatResult, MessageRole
from app.core.agent_engine import AgentEngine
from app.core.parallel import ToolExecutionResult
from app.core.session import AgentSession
from app.core.task_state_machine import TaskState


def tool_call(call_id="call-1", path="missing.txt"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": "read_file", "arguments": {"path": path}},
    }


@pytest.fixture
def harness(monkeypatch):
    # Bypass service initialization while retaining the real engine methods.
    engine = object.__new__(AgentEngine)
    engine._checkpoints = SimpleNamespace(save=AsyncMock())
    engine.tool_prioritizer = Mock()
    engine.tool_registry = Mock()
    engine._validate_tool_call = Mock(return_value=(True, ""))
    engine.debug_loop = None
    engine._send_completion_notification = Mock()
    persistence = AsyncMock(return_value=None)
    monkeypatch.setattr("app.core.agent_engine.persist_message", persistence)
    session = AgentSession(session_id="feedback-test", max_iterations=4)
    executor = SimpleNamespace(execute_all=AsyncMock())
    return engine, session, executor, persistence


async def collect(events):
    return [event async for event in events]


@pytest.mark.parametrize("sink", ["session", "persistence"])
@pytest.mark.parametrize(
    ("success", "error", "output", "expected"),
    [
        pytest.param(False, "timeout", "", "Tool execution failed: timeout", id="timeout"),
        pytest.param(False, "missing file", "", "Tool execution failed: missing file", id="missing"),
        pytest.param(False, "cancelled", "", "Tool execution failed: cancelled", id="cancelled"),
        pytest.param(False, "read failed", "first line", "Tool execution failed: read failed\n\nTool output:\nfirst line", id="partial"),
        pytest.param(False, "line1\nline2", "a\nb\n", "Tool execution failed: line1\nline2\n\nTool output:\na\nb\n", id="multiline"),
        pytest.param(False, "", "", "Tool execution failed: Tool execution failed without an error message.", id="empty-error"),
        pytest.param(False, "", "partial", "Tool execution failed: Tool execution failed without an error message.\n\nTool output:\npartial", id="empty-error-partial"),
        pytest.param(False, "failed", "0", "Tool execution failed: failed\n\nTool output:\n0", id="zero-text"),
        pytest.param(True, "", "", "", id="success-empty"),
        pytest.param(True, "", "  text\n\n", "  text\n\n", id="success-whitespace"),
        pytest.param(True, "", '{"ok": true}', '{"ok": true}', id="success-json"),
        pytest.param(True, "", "Tool execution failed: quoted output", "Tool execution failed: quoted output", id="success-error-like-text"),
    ],
)
def test_feedback_content(harness, sink, success, error, output, expected):
    engine, session, executor, persistence = harness
    tr = ToolExecutionResult(
        tool_name="read_file", tool_call_id="call-1", success=success,
        error=error, result=output, duration_ms=12.0,
    )
    calls = [tool_call()]
    executor.execute_all.return_value = [tr]
    events = asyncio.run(collect(engine._handle_tool_execution(
        session, executor, ChatResult(tool_calls=calls), 1, 42,
    )))

    if sink == "session":
        assert session.messages[-1] == {
            "role": MessageRole.TOOL, "content": expected, "tool_call_id": "call-1",
        }
    else:
        assert persistence.await_args_list == [
            call(session.session_id, MessageRole.ASSISTANT, content="", tool_calls=calls),
            call(session.session_id, MessageRole.TOOL, content=expected,
                 tool_name="read_file", tool_call_id="call-1"),
        ]
    executor.execute_all.assert_awaited_once_with(calls)
    engine._validate_tool_call.assert_called_once_with(session, "read_file", {"path": "missing.txt"})
    assert [event.type for event in events] == [
        AgentEventType.TOOL_CALL, AgentEventType.TOOL_RESULT, AgentEventType.CHECKPOINT,
    ]
    assert session.metrics.total_tool_calls == 1
    engine._checkpoints.save.assert_awaited_once()


@pytest.mark.parametrize("recovered", [True, False])
def test_feedback_uses_real_debug_outcome(harness, recovered):
    engine, session, executor, persistence = harness
    tr = ToolExecutionResult(
        tool_name="read_file", tool_call_id="call-1", success=False,
        error="original failure", result="original partial", arguments={"path": "missing.txt"},
    )
    engine.debug_loop = SimpleNamespace(recover=AsyncMock(return_value=SimpleNamespace(
        success=recovered, output="recovered output",
    )))
    executor.execute_all.return_value = [tr]
    asyncio.run(collect(engine._handle_tool_execution(
        session, executor, ChatResult(tool_calls=[tool_call()]), 1, 42,
    )))

    expected = "recovered output" if recovered else (
        "Tool execution failed: original failure\n\nTool output:\noriginal partial"
    )
    assert session.messages[-1]["content"] == expected
    assert persistence.await_args.kwargs["content"] == expected
    assert tr.success is recovered
    assert tr.error == ("" if recovered else "original failure")
    assert session.debug_attempts == {"read_file": 1}
    engine.debug_loop.recover.assert_awaited_once()
    assert engine.debug_loop.recover.await_args.kwargs["error_output"] == "original failure"


def test_feedback_when_debug_attempts_exhausted(harness):
    engine, session, executor, persistence = harness
    session.debug_attempts["read_file"] = 3
    engine.debug_loop = SimpleNamespace(recover=AsyncMock())
    executor.execute_all.return_value = [ToolExecutionResult(
        tool_name="read_file", tool_call_id="call-1", success=False,
        error="still failed", result="partial",
    )]
    asyncio.run(collect(engine._handle_tool_execution(
        session, executor, ChatResult(tool_calls=[tool_call()]), 1, 42,
    )))
    expected = "Tool execution failed: still failed\n\nTool output:\npartial"
    assert session.messages[-1]["content"] == expected
    assert persistence.await_args.kwargs["content"] == expected
    engine.debug_loop.recover.assert_not_awaited()


def test_iteration_loop_exposes_failure_then_success_to_scripted_model(harness, monkeypatch):
    engine, session, executor, persistence = harness
    expected_error = "Tool execution failed: missing file\n\nTool output:\ntry available.txt"
    seen = []

    async def scripted_chat(*, messages, tools):
        seen.append(deepcopy(messages))
        assert tools is None
        if len(seen) == 1:
            return ChatResult(tool_calls=[tool_call()])
        if len(seen) == 2 and messages[-1]["content"] == expected_error:
            return ChatResult(tool_calls=[tool_call("call-2", "available.txt")])
        if len(seen) == 3 and messages[-1]["content"] == "file contents":
            return ChatResult(content="Scripted recovery complete.")
        return ChatResult(content="Scripted feedback contract missing.")

    adapter = SimpleNamespace(
        capabilities=SimpleNamespace(streaming=False, max_tokens=100000),
        chat=AsyncMock(side_effect=scripted_chat),
    )
    engine.model_registry = SimpleNamespace(get_or_create=Mock(return_value=adapter))
    monkeypatch.setattr("app.core.agent_engine.build_tools", Mock(return_value=[]))
    compressor = SimpleNamespace(needs_compression=Mock(return_value=False), compress=AsyncMock())
    executor.execute_all.side_effect = [
        [ToolExecutionResult(tool_name="read_file", tool_call_id="call-1",
                             success=False, error="missing file", result="try available.txt")],
        [ToolExecutionResult(tool_name="read_file", tool_call_id="call-2", result="file contents")],
    ]
    session.messages.append({"role": MessageRole.USER, "content": "Read the available file."})

    async def run():
        await session.state_machine.transition(TaskState.PROCESSING)
        return await collect(engine._iteration_loop(session, executor, compressor))

    events = asyncio.run(run())
    assert len(seen) == 3
    assert seen[1][-1]["content"] == expected_error
    assert seen[2][-1]["content"] == "file contents"
    assert executor.execute_all.await_args_list == [
        call([tool_call()]), call([tool_call("call-2", "available.txt")]),
    ]
    persisted_tools = [c.kwargs["content"] for c in persistence.await_args_list
                       if c.args[1] == MessageRole.TOOL]
    assert persisted_tools == [expected_error, "file contents"]
    assert session.messages[-1]["content"] == "Scripted recovery complete."
    assert session.state_machine.state == TaskState.COMPLETED
    assert session.metrics.total_iterations == 3
    assert session.metrics.total_tool_calls == 2
    assert sum(event.type == AgentEventType.TOOL_RESULT for event in events) == 2
    assert engine._checkpoints.save.await_count == 3
    compressor.compress.assert_not_awaited()
