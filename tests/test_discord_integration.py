"""Tests for discord integration."""

import pytest

from app.integrations.discord_integration import (
    DiscordIntegration,
    DiscordIntegrationConfig,
)


class TestDiscordIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = DiscordIntegrationConfig(api_key='test-key')
        integration = DiscordIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = DiscordIntegrationConfig(api_key='test-key')
        integration = DiscordIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
