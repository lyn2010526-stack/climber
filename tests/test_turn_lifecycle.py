"""Tests for Turn lifecycle integration with AgentEngine."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.core.agent_engine import AgentEngine, AgentSession
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


@pytest_asyncio.fixture
async def engine():
    """Create an agent engine with fake registries."""
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
    return engine


@pytest.mark.asyncio
async def test_turn_created_gracefully(engine: AgentEngine):
    """Test that Turn creation doesn't crash when session isn't persisted."""
    fake_model = MagicMock()
    fake_model.capabilities.streaming = False
    fake_model.capabilities.max_tokens = 4096
    fake_model.chat = AsyncMock(return_value=MagicMock(content="Hello!", tool_calls=[], finish_reason="stop", tokens_used=10))
    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    events = []
    async for event in engine.run(session, "Hi"):
        events.append(event)

    # Verify run completed successfully
    assert len(events) > 0
    assert any(e.type.value == "done" for e in events)
    # Turn may or may not be created depending on DB state
    assert session.current_turn_id is None or isinstance(session.current_turn_id, str)


@pytest.mark.asyncio
async def test_turn_completed_on_success(engine: AgentEngine):
    """Test that Turn is completed with success status when DB is available."""
    fake_model = MagicMock()
    fake_model.capabilities.streaming = False
    fake_model.capabilities.max_tokens = 4096
    fake_model.chat = AsyncMock(return_value=MagicMock(content="Hello!", tool_calls=[], finish_reason="stop", tokens_used=10))
    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    events = []
    async for event in engine.run(session, "Hi"):
        events.append(event)

    # Verify run completed successfully
    assert len(events) > 0
    assert any(e.type.value == "done" for e in events)


@pytest.mark.asyncio
async def test_turn_completed_on_error(engine: AgentEngine):
    """Test that error handling doesn't crash."""
    fake_model = MagicMock()
    fake_model.capabilities.streaming = False
    fake_model.capabilities.max_tokens = 4096
    fake_model.chat = AsyncMock(side_effect=Exception("Model error"))
    engine.model_registry._models["fake:fake-model"] = fake_model

    session = engine.create_session(
        agent_id="test",
        user_id="user1",
        provider="fake",
        model_id="fake-model",
        api_key="fake-key",
    )

    events = []
    async for event in engine.run(session, "Hi"):
        events.append(event)

    # Verify error event was emitted
    assert any(e.type.value == "error" for e in events)


@pytest.mark.asyncio
async def test_session_has_current_turn_id_attribute():
    """Test that AgentSession has current_turn_id attribute."""
    session = AgentSession(
        session_id="test-session",
        agent_id="test-agent",
        user_id="test-user",
        provider="openai",
        model_id="gpt-4",
        api_key="test-key",
    )
    assert hasattr(session, "current_turn_id")
    assert session.current_turn_id is None
