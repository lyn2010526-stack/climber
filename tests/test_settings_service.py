"""Tests for settings service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.settings_service import SettingsService
from app.storage.models_settings import McpStatus, UserSettings


def _create_mock_result(value):
    """Create a mock async result with scalar_one_or_none."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=value)
    return mock_result


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestSettingsService:
    @pytest.mark.asyncio
    async def test_get_settings_creates_default(self, mock_db):
        """Test that default settings are created if not exists."""
        mock_db.execute.return_value = _create_mock_result(None)

        service = SettingsService(mock_db)
        settings = await service.get_settings("user-123")

        assert settings.user_id == "user-123"
        assert settings.autonomous_agent_mode is False
        assert settings.token_throttle_mcp_enabled is False
        assert settings.mcp_status == McpStatus.DISCONNECTED
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_settings_existing(self, mock_db):
        """Test getting existing settings."""
        existing = UserSettings(
            id="settings-123",
            user_id="user-123",
            autonomous_agent_mode=True,
            token_throttle_mcp_enabled=True,
            mcp_status=McpStatus.READY,
        )
        mock_db.execute.return_value = _create_mock_result(existing)

        service = SettingsService(mock_db)
        settings = await service.get_settings("user-123")

        assert settings.autonomous_agent_mode is True
        assert settings.token_throttle_mcp_enabled is True
        assert settings.mcp_status == McpStatus.READY
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_settings(self, mock_db):
        """Test updating settings."""
        existing = UserSettings(
            id="settings-123",
            user_id="user-123",
            autonomous_agent_mode=False,
            token_throttle_mcp_enabled=False,
        )
        mock_db.execute.return_value = _create_mock_result(existing)

        service = SettingsService(mock_db)
        updated = await service.update_settings(
            user_id="user-123",
            autonomous_agent_mode=True,
        )

        assert updated.autonomous_agent_mode is True
        assert updated.token_throttle_mcp_enabled is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_mcp_status(self, mock_db):
        """Test updating MCP status."""
        existing = UserSettings(
            id="settings-123",
            user_id="user-123",
            autonomous_agent_mode=False,
            token_throttle_mcp_enabled=True,
            mcp_status=McpStatus.DISCONNECTED,
        )
        mock_db.execute.return_value = _create_mock_result(existing)

        service = SettingsService(mock_db)
        await service.update_mcp_status("user-123", McpStatus.READY)

        assert existing.mcp_status == McpStatus.READY
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_effective_mode(self, mock_db):
        """Test getting effective mode."""
        existing = UserSettings(
            id="settings-123",
            user_id="user-123",
            autonomous_agent_mode=True,
            token_throttle_mcp_enabled=True,
            mcp_status=McpStatus.READY,
        )
        mock_db.execute.return_value = _create_mock_result(existing)

        service = SettingsService(mock_db)
        mode = service.get_effective_mode(existing)

        assert mode["autonomous_agent_mode"] is True
        assert mode["token_throttle_mcp_enabled"] is True
        assert mode["mcp_status"] == "ready"
        assert mode["mcp_ready"] is True
