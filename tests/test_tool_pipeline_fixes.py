"""Tests for tool_pipeline.py and agent_engine.py bug fixes."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import MessageRole
from app.core.agent_engine import AgentEngine, AgentSession
from app.core.task_state_machine import TaskState, TaskStateMachine
from app.core.tool_pipeline import ToolExecutionPipeline, ToolExecutionResult


class TestToolCallIdPropagation:
    """Test that tool_call_id is correctly propagated through the pipeline."""

    def test_tool_execution_result_has_tool_call_id_field(self):
        """ToolExecutionResult should accept and store tool_call_id."""
        result = ToolExecutionResult(
            tool_name="search",
            result="found",
            error=None,
            success=True,
            arguments={"query": "test"},
            tool_call_id="call_abc123",
        )
        assert result.tool_call_id == "call_abc123"

    def test_tool_call_id_defaults_to_empty_string(self):
        """tool_call_id should default to empty string for backward compatibility."""
        result = ToolExecutionResult(
            tool_name="search",
            result="found",
            error=None,
            success=True,
        )
        assert result.tool_call_id == ""

    @pytest.mark.asyncio
    async def test_execute_propagates_tool_call_id(self):
        """The execute method should extract tool_call_id from tool_calls and propagate it."""
        executor = AsyncMock()
        executor.execute_all = AsyncMock(return_value=[
            MagicMock(tool_name="search", result="data", error=None, success=True, duration_ms=10),
        ])
        prioritizer = MagicMock()
        pipeline = ToolExecutionPipeline(executor=executor, prioritizer=prioritizer)

        tool_calls = [
            {"id": "call_xyz", "type": "function", "function": {"name": "search", "arguments": '{"query": "test"}'}},
        ]
        session = MagicMock()
        session.debug_attempts = {}

        results = await pipeline.execute(tool_calls, session)

        assert len(results) == 1
        assert results[0].tool_call_id == "call_xyz"


class TestMultipleCallsSameTool:
    """Test that multiple calls to the same tool don't mix up results."""

    @pytest.mark.asyncio
    async def test_multiple_calls_preserve_order_by_id(self):
        """When calling the same tool multiple times, results should match by tool_call_id."""
        executor = AsyncMock()
        executor.execute_all = AsyncMock(return_value=[
            MagicMock(tool_name="read_file", result="content_a", error=None, success=True, duration_ms=5),
        ])
        prioritizer = MagicMock()
        pipeline = ToolExecutionPipeline(executor=executor, prioritizer=prioritizer)

        tool_calls = [
            {"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "a.txt"}'}},
            {"id": "call_2", "type": "function", "function": {"name": "read_file", "arguments": '{"path": "b.txt"}'}},
        ]
        session = MagicMock()
        session.debug_attempts = {}

        results = await pipeline.execute(tool_calls, session)

        assert len(results) == 2
        assert results[0].tool_call_id == "call_1"
        assert results[1].tool_call_id == "call_2"

    def test_to_events_includes_tool_call_id(self):
        """to_events should include tool_call_id in TOOL_RESULT events."""
        executor = AsyncMock()
        prioritizer = MagicMock()
        pipeline = ToolExecutionPipeline(executor=executor, prioritizer=prioritizer)

        results = [
            ToolExecutionResult(tool_name="search", result="r1", error=None, success=True, tool_call_id="call_a"),
            ToolExecutionResult(tool_name="search", result="r2", error=None, success=True, tool_call_id="call_b"),
        ]
        tool_calls = [
            {"id": "call_a", "type": "function", "function": {"name": "search", "arguments": {"query": "q1"}}},
            {"id": "call_b", "type": "function", "function": {"name": "search", "arguments": {"query": "q2"}}},
        ]

        events = pipeline.to_events(results, tool_calls)

        # First two events are TOOL_CALL, next two are TOOL_RESULT
        tool_result_events = [e for e in events if e.data.get("tool_call_id")]
        assert len(tool_result_events) == 2
        assert tool_result_events[0].data["tool_call_id"] == "call_a"
        assert tool_result_events[1].data["tool_call_id"] == "call_b"


class TestDebugMethodsRemoved:
    """Test that debug loop methods are removed from AgentEngine."""

    def test_agent_engine_has_no_should_debug(self):
        """AgentEngine should not have _should_debug method."""
        assert not hasattr(AgentEngine, "_should_debug")

    def test_agent_engine_has_no_attempt_debug(self):
        """AgentEngine should not have _attempt_debug method."""
        assert not hasattr(AgentEngine, "_attempt_debug")


class TestSessionStatusReadOnly:
    """Test that session status is read-only and derived from state machine."""

    def test_status_is_read_only(self):
        """Session status should be a read-only property."""
        session = AgentSession(
            session_id="test-1",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        # Verify it's a property, not a settable attribute
        assert isinstance(AgentSession.status, property)

        # Verify setting raises AttributeError
        with pytest.raises(AttributeError):
            session.status = "running"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_status_reflects_state_machine(self):
        """Session status should match the state machine's current state value."""
        session = AgentSession(
            session_id="test-2",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        assert session.status == "pending"

        await session.state_machine.transition(TaskState.PROCESSING, trigger="test")
        assert session.status == "running"

        await session.state_machine.transition(TaskState.COMPLETED, trigger="test")
        assert session.status == "completed"

    def test_status_returns_string(self):
        """Status should return a plain string, not an enum."""
        session = AgentSession(
            session_id="test-3",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        result = session.status
        assert isinstance(result, str)


class TestAppendToMessages:
    """Test that append_to_messages includes tool_call_id."""

    def test_append_includes_tool_call_id(self):
        """append_to_messages should include tool_call_id in message dict."""
        executor = AsyncMock()
        prioritizer = MagicMock()
        pipeline = ToolExecutionPipeline(executor=executor, prioritizer=prioritizer)

        session = MagicMock()
        session.messages = []

        results = [
            ToolExecutionResult(tool_name="search", result="data", error=None, success=True, tool_call_id="call_123"),
        ]

        pipeline.append_to_messages(session, results)

        assert len(session.messages) == 1
        msg = session.messages[0]
        assert msg["role"] == MessageRole.TOOL
        assert msg["tool_call_id"] == "call_123"
        assert msg["name"] == "search"
        assert msg["content"] == "data"


class TestFireAndForgetTracking:
    """Test that fire-and-forget tasks are tracked."""

    def test_pending_tasks_initialized(self):
        """AgentSession should have a _pending_tasks set."""
        session = AgentSession(
            session_id="test-4",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )
        assert hasattr(session, "_pending_tasks")
        assert isinstance(session._pending_tasks, set)
        assert len(session._pending_tasks) == 0

    @pytest.mark.asyncio
    async def test_fire_and_forget_creates_tracked_task(self):
        """_fire_and_forget should create a task and track it."""
        session = AgentSession(
            session_id="test-5",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )

        async def dummy_coro():
            await asyncio.sleep(0.01)
            return "done"

        session._fire_and_forget(dummy_coro())
        assert len(session._pending_tasks) == 1
        await session._await_pending_tasks()

    @pytest.mark.asyncio
    async def test_await_pending_tasks_clears_set(self):
        """_await_pending_tasks should await all tasks and clear the set."""
        session = AgentSession(
            session_id="test-6",
            agent_id="agent-1",
            user_id="user-1",
            provider="openai",
            model_id="gpt-4",
            api_key="sk-test",
        )

        async def quick_coro():
            return "done"

        session._fire_and_forget(quick_coro())
        session._fire_and_forget(quick_coro())
        assert len(session._pending_tasks) == 2

        await session._await_pending_tasks()
        assert len(session._pending_tasks) == 0
