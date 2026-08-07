"""Tests for slack integration."""

import pytest

from app.integrations.slack_integration import (
    SlackIntegration,
    SlackIntegrationConfig,
)


class TestSlackIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = SlackIntegrationConfig(api_key='test-key')
        integration = SlackIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = SlackIntegrationConfig(api_key='test-key')
        integration = SlackIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
