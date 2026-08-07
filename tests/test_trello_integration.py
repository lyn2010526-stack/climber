"""Tests for trello integration."""

import pytest

from app.integrations.trello_integration import (
    TrelloIntegration,
    TrelloIntegrationConfig,
)


class TestTrelloIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = TrelloIntegrationConfig(api_key='test-key')
        integration = TrelloIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = TrelloIntegrationConfig(api_key='test-key')
        integration = TrelloIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
