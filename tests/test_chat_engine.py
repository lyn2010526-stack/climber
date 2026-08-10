"""Tests for chat engine integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.chat_engine import ChatEngine
from app.core.mcp_controller import McpStatus
from app.core.prompt_manager import PromptManager
from app.services.settings_service import SettingsService
from app.storage.models_settings import McpStatus as ModelMcpStatus
from app.storage.models_settings import UserSettings


@pytest.fixture
def mock_prompt_manager():
    manager = MagicMock(spec=PromptManager)
    manager.assemble_prompt.return_value = "base prompt + autonomous + mcp"
    manager.get_active_constraints.return_value = ["autonomous_agent", "token_throttle_mcp"]
    return manager


@pytest.fixture
def mock_mcp_controller():
    controller = MagicMock()
    controller.get_status.return_value = McpStatus.READY
    return controller


@pytest.fixture
def mock_settings_service():
    service = MagicMock(spec=SettingsService)
    settings = UserSettings(
        id="settings-123",
        user_id="user-123",
        autonomous_agent_mode=True,
        token_throttle_mcp_enabled=True,
        mcp_status=ModelMcpStatus.READY,
    )
    service.get_settings.return_value = settings
    return service


@pytest.mark.asyncio
async def test_get_system_prompt_both_enabled(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test system prompt assembly with both modes enabled."""
    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    prompt = await engine.get_system_prompt("user-123")

    mock_settings_service.get_settings.assert_called_once_with("user-123")
    mock_prompt_manager.assemble_prompt.assert_called_once_with(
        autonomous_mode=True, mcp_ready=True
    )
    assert "base prompt" in prompt


@pytest.mark.asyncio
async def test_get_system_prompt_autonomous_only(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test system prompt with only autonomous mode."""
    mock_settings_service.get_settings.return_value = UserSettings(
        id="settings-123",
        user_id="user-123",
        autonomous_agent_mode=True,
        token_throttle_mcp_enabled=False,
        mcp_status=ModelMcpStatus.DISCONNECTED,
    )
    mock_mcp_controller.get_status.return_value = McpStatus.DISCONNECTED

    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    await engine.get_system_prompt("user-123")

    mock_prompt_manager.assemble_prompt.assert_called_once_with(
        autonomous_mode=True, mcp_ready=False
    )


@pytest.mark.asyncio
async def test_ensure_mcp_ready_starts_when_disconnected(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test MCP start when disconnected."""
    mock_mcp_controller.get_status.return_value = McpStatus.DISCONNECTED
    mock_mcp_controller.start = AsyncMock(
        return_value=MagicMock(success=True, status=McpStatus.READY)
    )

    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    result = await engine.ensure_mcp_ready("user-123")

    mock_settings_service.get_settings.assert_called_once_with("user-123")
    mock_mcp_controller.start.assert_called_once()
    mock_settings_service.update_mcp_status.assert_called_once_with("user-123", McpStatus.READY)
    assert result == McpStatus.READY


@pytest.mark.asyncio
async def test_ensure_mcp_ready_skips_when_disabled(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test MCP not started when disabled."""
    mock_settings_service.get_settings.return_value = UserSettings(
        id="settings-123",
        user_id="user-123",
        autonomous_agent_mode=False,
        token_throttle_mcp_enabled=False,
        mcp_status=ModelMcpStatus.DISCONNECTED,
    )

    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    result = await engine.ensure_mcp_ready("user-123")

    mock_mcp_controller.start.assert_not_called()
    assert result == McpStatus.DISCONNECTED


@pytest.mark.asyncio
async def test_get_active_constraints(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test getting active constraints."""
    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    constraints = await engine.get_active_constraints("user-123")

    assert "autonomous_agent" in constraints
    assert "token_throttle_mcp" in constraints
    mock_prompt_manager.get_active_constraints.assert_called_once_with(
        autonomous_mode=True, mcp_ready=True
    )


@pytest.mark.asyncio
async def test_get_effective_mode(
    mock_prompt_manager, mock_mcp_controller, mock_settings_service
):
    """Test getting effective mode."""
    mock_mcp_controller.get_status.return_value = McpStatus.READY

    engine = ChatEngine(mock_prompt_manager, mock_mcp_controller, mock_settings_service)
    mode = await engine.get_effective_mode("user-123")

    assert mode["autonomous_agent_mode"] is True
    assert mode["token_throttle_mcp_enabled"] is True
    assert mode["mcp_status"] == "ready"
    assert mode["mcp_ready"] is True
