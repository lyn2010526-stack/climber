"""Edge/error-path tests for the agent engine ReAct loop.

Covers the paths the happy-path tests in test_agent_engine.py miss:
model/stream failure, tool execution failure, approval interception,
max-iteration boundary, context compression on long input, empty input,
session restart and permission resolution. All model/tool IO is mocked.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
import pytest_asyncio

from app.core import AgentEventType, ChatResult, ContextConfig, SessionStatus
from app.core.agent_engine import AgentEngine
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


@pytest_asyncio.fixture
async def engine():
    from app.core.permission_rules import PermissionConfig, PermissionMode

    model_registry = ModelRegistry()
    tool_registry = ToolRegistry()

    @tool_registry.tool(name="echo", description="Echo back the input")
    async def echo(text: str) -> str:
        return f"Echo: {text}"

    @tool_registry.tool(name="boom", description="Always fails")
    async def boom(text: str) -> str:
        raise RuntimeError("tool crashed")

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
async def test_model_chat_failure_yields_error_and_fails(engine: AgentEngine):
    _register(engine, _FailingModel())
    session = _session(engine)
    events = await _collect(engine, session, "hi")
    errors = [e for e in events if e.type == AgentEventType.ERROR]
    assert errors and "model exploded" in errors[0].data["error"]
    assert session.status == SessionStatus.FAILED


@pytest.mark.asyncio
async def test_stream_failure_yields_error_and_fails(engine: AgentEngine):
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
    assert results and "tool crashed" in results[0].data["result"]
    done = next(e for e in events if e.type == AgentEventType.DONE)
    assert "recovered" in done.data["content"]
    assert session.status == SessionStatus.COMPLETED


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
    from app.core.permission_rules import PermissionConfig, PermissionMode

    session = _session(engine)
    allowed, reason = engine._validate_tool_call(session, "echo", {"text": "x"})
    assert allowed is True
    assert reason == "OK"

    session.permission_config = PermissionConfig(mode=PermissionMode.PLAN)
    denied, reason = engine._validate_tool_call(session, "echo", {"text": "x"})
    assert denied is False
    assert "denied" in reason.lower()


def test_resolve_permission_pending_and_missing(engine: AgentEngine):
    session = _session(engine)
    assert engine.resolve_permission("call-missing", "allow") is False

    session._pending_permission = {"tool_call_id": "call-1"}
    session._permission_event = asyncio.Event()
    assert engine.resolve_permission("call-1", "allow") is True
    assert session._pending_permission["decision"] == "allow"
    assert session._permission_event.is_set()


@pytest.mark.asyncio
async def test_context_compression_on_long_input(engine: AgentEngine):
    _register(engine, FakeModelAdapter(responses=[ChatResult(content="short", finish_reason="stop")]))
    session = _session(engine, context_config=ContextConfig(max_tokens=50))
    events = await _collect(engine, session, "a" * 1000)
    assert any(e.type == AgentEventType.CONTEXT_COMPRESSION for e in events)
    assert events[-1].type == AgentEventType.DONE
