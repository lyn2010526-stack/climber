"""Tests for the agent engine core."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio

from app.core import AgentEventType, ChatResult, SessionStatus
from app.core.agent_engine import AgentEngine
from app.models import ModelCapability
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


class FakeModelAdapter:
    """A mock model adapter for testing."""

    provider = "fake"
    model_id = "fake-model"

    def __init__(self, responses: list[ChatResult] | None = None):
        self._responses = responses or [ChatResult(content="Default response")]
        self._call_count = 0

    @property
    def api_key(self) -> str:
        return "fake"

    @api_key.setter
    def api_key(self, value: str) -> None:
        pass

    @property
    def capabilities(self) -> ModelCapability:
        return ModelCapability(chat=True, streaming=False, tools=True, max_tokens=4096)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        result = await self.chat(messages, tools, **kwargs)
        if result.content:
            yield ChatResult(content=result.content, tool_calls=[], finish_reason="stop", tokens_used=result.tokens_used)
        yield result


class StreamingFakeModelAdapter(FakeModelAdapter):
    """A mock adapter that supports streaming."""

    def __init__(self, responses: list[ChatResult] | None = None, stream_chunks: list[list[str]] | None = None):
        super().__init__(responses)
        self._stream_chunks = stream_chunks or []

    @property
    def capabilities(self) -> ModelCapability:
        return ModelCapability(chat=True, streaming=True, tools=True, max_tokens=4096)

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatResult]:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        chunks = self._stream_chunks[idx] if idx < len(self._stream_chunks) else [self._responses[idx].content]
        for chunk_text in chunks:
            yield ChatResult(content=chunk_text, tool_calls=[], finish_reason="stop", tokens_used=10)
        yield self._responses[idx]


@pytest_asyncio.fixture
async def engine():
    """Create an agent engine with fake registries."""
    from app.core.permission_rules import PermissionConfig, PermissionMode

    model_registry = ModelRegistry()
    tool_registry = ToolRegistry()

    @tool_registry.tool(name="echo", description="Echo back the input")
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    @tool_registry.tool(name="add", description="Add two numbers")
    async def add(a: float, b: float) -> str:
        return str(a + b)

    engine = AgentEngine(
        model_registry=model_registry,
        tool_registry=tool_registry,
    )
    # Use BYPASS permission mode for tests to avoid ASK blocking
    engine._default_permission_config = PermissionConfig(mode=PermissionMode.BYPASS)
    return engine


@pytest.mark.asyncio
async def test_simple_conversation(engine: AgentEngine):
    """Test a simple text-only conversation (no tool calls)."""
    fake_model = FakeModelAdapter(
        responses=[
            ChatResult(content="Hello! How can I help?", finish_reason="stop")
        ]
    )

    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
        system_prompt="You are a helpful assistant.",
    )

    events: list = []
    async for event in engine.run(session, "Hi there"):
        events.append(event)

    types = [e.type for e in events]
    assert AgentEventType.TEXT in types
    assert AgentEventType.DONE in types
    assert session.status.value == "completed"

    done_event = [e for e in events if e.type == AgentEventType.DONE][0]
    assert "Hello!" in done_event.data.get("content", "")


@pytest.mark.asyncio
async def test_streaming_conversation(engine: AgentEngine):
    """Test streaming adapter yields token-level events."""
    fake_model = StreamingFakeModelAdapter(
        responses=[ChatResult(content="Hello world", finish_reason="stop")],
        stream_chunks=[["Hello", " world"]],
    )

    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    events: list = []
    async for event in engine.run(session, "Hi"):
        events.append(event)

    text_events = [e for e in events if e.type == AgentEventType.TEXT]
    # Should have token-level events
    assert len(text_events) >= 2  # At least "Hello" and " world"
    # Final content should be complete
    done_event = [e for e in events if e.type == AgentEventType.DONE][0]
    assert "Hello world" in done_event.data.get("content", "")


@pytest.mark.asyncio
async def test_tool_call_flow(engine: AgentEngine):
    """Test a conversation that involves a tool call."""
    fake_model = FakeModelAdapter(
        responses=[
            ChatResult(
                content="",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": {"text": "hello world"}},
                }],
            ),
            ChatResult(content="The echo result is: Echo: hello world"),
        ]
    )

    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
        tools=["echo"],
    )

    events: list = []
    async for event in engine.run(session, "Echo hello world"):
        events.append(event)

    types = [e.type for e in events]
    assert AgentEventType.DONE in types

    done_event = [e for e in events if e.type == AgentEventType.DONE][0]
    assert "Echo: hello world" in done_event.data.get("content", "")


@pytest.mark.asyncio
async def test_session_stop(engine: AgentEngine):
    """Test stopping a running session."""

    class SlowModel(FakeModelAdapter):
        async def chat(self, messages, tools=None, **kwargs):
            await asyncio.sleep(0.1)
            return ChatResult(content="response")

    slow = SlowModel()
    engine.model_registry._models["fake:fake-model"] = slow

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    async def stop_later():
        await asyncio.sleep(0.05)
        session.stop()

    asyncio.create_task(stop_later())

    events: list = []
    async for event in engine.run(session, "test"):
        events.append(event)

    assert session.status in (SessionStatus.STOPPED, SessionStatus.COMPLETED)


def test_tool_registry_infer_schema():
    """Test that tool parameter schema is inferred from function signature."""
    registry = ToolRegistry()

    @registry.tool(name="greet", description="Greet someone")
    async def greet(name: str, times: int = 1) -> str:
        return "hi"

    tools = registry.get_openai_tools()
    assert len(tools) == 1
    func = tools[0]["function"]
    assert func["name"] == "greet"
    assert "name" in func["parameters"]["properties"]
    assert "times" in func["parameters"]["properties"]
    assert func["parameters"]["properties"]["times"]["type"] == "integer"


def test_tool_registry_get_tool_existing():
    """Test that get_tool returns a definition for a registered tool."""
    registry = ToolRegistry()

    @registry.tool(name="echo", description="Echo back the input")
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    result = registry.get_tool("echo")
    assert result is not None
    assert result.name == "echo"
    assert result.description == "Echo back the input"
    assert result.type == "function"


def test_tool_registry_get_tool_missing():
    """Test that get_tool returns None for non-existent tool."""
    registry = ToolRegistry()

    @registry.tool(name="echo", description="Echo back the input")
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    result = registry.get_tool("nonexistent")
    assert result is None


def test_tool_registry_get_openai_tools_format():
    """Test that get_openai_tools returns correct format."""
    registry = ToolRegistry()

    @registry.tool(name="add", description="Add two numbers")
    async def add(a: float, b: float) -> str:
        return str(a + b)

    tools = registry.get_openai_tools()
    assert len(tools) == 1
    tool = tools[0]
    assert tool["type"] == "function"
    assert "function" in tool
    assert tool["function"]["name"] == "add"
    assert tool["function"]["description"] == "Add two numbers"
    assert "parameters" in tool["function"]
    assert "a" in tool["function"]["parameters"]["properties"]
    assert "b" in tool["function"]["parameters"]["properties"]
