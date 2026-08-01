"""Tests for ToolExecutionPipeline."""

from __future__ import annotations

import pytest

from app.core.tool_pipeline import ToolExecutionPipeline, ToolExecutionResult
from app.core import AgentEventType


class FakeExecutor:
    """Fake tool executor for testing."""

    def __init__(self, results=None):
        self._results = results or []
        self.calls = []

    async def execute_all(self, tool_calls):
        self.calls.append(tool_calls)
        return self._results

    async def execute(self, tool_name, arguments):
        return "result"


class FakeToolResult:
    """Fake tool result."""

    def __init__(self, tool_name="test", result="ok", error=None, success=True, duration_ms=10):
        self.tool_name = tool_name
        self.result = result
        self.error = error
        self.success = success
        self.duration_ms = duration_ms
        self.arguments = {}


class FakePrioritizer:
    """Fake tool prioritizer for testing."""

    def __init__(self):
        self.calls = []

    def record_outcome(self, tool_name, success, duration_ms):
        self.calls.append({"tool_name": tool_name, "success": success, "duration_ms": duration_ms})

    def rank_tools(self, task_description, available):
        return [t["function"]["name"] for t in available]


class FakeSession:
    """Fake session for testing."""

    def __init__(self):
        self.messages = []
        self.debug_attempts: dict[str, int] = {}


@pytest.mark.asyncio
async def test_execute_runs_tools_in_parallel():
    """Test that execute runs tools and returns results."""
    results = [
        FakeToolResult(tool_name="echo", result="hello", success=True),
    ]
    executor = FakeExecutor(results=results)
    prioritizer = FakePrioritizer()
    pipeline = ToolExecutionPipeline(
        executor=executor,
        prioritizer=prioritizer,
    )

    session = FakeSession()
    tool_calls = [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "echo", "arguments": {"text": "hello"}},
    }]

    pipeline_results = await pipeline.execute(tool_calls, session)

    assert len(pipeline_results) == 1
    assert pipeline_results[0].tool_name == "echo"
    assert pipeline_results[0].result == "hello"
    assert pipeline_results[0].success is True

    # Verify prioritizer recorded outcome
    assert len(prioritizer.calls) == 1
    assert prioritizer.calls[0]["tool_name"] == "echo"


@pytest.mark.asyncio
async def test_execute_handles_tool_failure():
    """Test that execute handles tool failures gracefully."""
    results = [
        FakeToolResult(tool_name="fail_tool", result="", error="Tool error", success=False),
    ]
    executor = FakeExecutor(results=results)
    prioritizer = FakePrioritizer()
    pipeline = ToolExecutionPipeline(
        executor=executor,
        prioritizer=prioritizer,
    )

    session = FakeSession()
    tool_calls = [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "fail_tool", "arguments": {}},
    }]

    pipeline_results = await pipeline.execute(tool_calls, session)

    assert len(pipeline_results) == 1
    assert pipeline_results[0].tool_name == "fail_tool"
    assert pipeline_results[0].success is False
    assert pipeline_results[0].error == "Tool error"


@pytest.mark.asyncio
async def test_to_events_converts_results():
    """Test that to_events converts results to AgentEvents."""
    executor = FakeExecutor()
    prioritizer = FakePrioritizer()
    pipeline = ToolExecutionPipeline(
        executor=executor,
        prioritizer=prioritizer,
    )

    tool_calls = [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "echo", "arguments": {"text": "hello"}},
    }]
    results = [
        ToolExecutionResult(tool_name="echo", result="hello", error=None, success=True, arguments={"text": "hello"}),
    ]

    events = pipeline.to_events(results, tool_calls)

    assert len(events) == 2
    assert events[0].type == AgentEventType.TOOL_CALL
    assert events[0].data["name"] == "echo"
    assert events[1].type == AgentEventType.TOOL_RESULT
    assert events[1].data["tool_name"] == "echo"
    assert events[1].data["result"] == "hello"


@pytest.mark.asyncio
async def test_append_to_messages():
    """Test that append_to_messages adds results to session."""
    executor = FakeExecutor()
    prioritizer = FakePrioritizer()
    pipeline = ToolExecutionPipeline(
        executor=executor,
        prioritizer=prioritizer,
    )

    session = FakeSession()
    results = [
        ToolExecutionResult(tool_name="echo", result="hello", error=None, success=True),
        ToolExecutionResult(tool_name="add", result="3", error=None, success=True),
    ]

    pipeline.append_to_messages(session, results)

    assert len(session.messages) == 2
    assert session.messages[0]["role"] == "tool"
    assert session.messages[0]["name"] == "echo"
    assert session.messages[0]["content"] == "hello"
    assert session.messages[0]["tool_call_id"] == ""
    assert session.messages[1]["name"] == "add"
    assert session.messages[1]["content"] == "3"
    assert session.messages[1]["tool_call_id"] == ""
