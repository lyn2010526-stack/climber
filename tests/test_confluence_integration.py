"""Tests for confluence integration."""

import pytest

from app.integrations.confluence_integration import (
    ConfluenceIntegration,
    ConfluenceIntegrationConfig,
)


class TestConfluenceIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = ConfluenceIntegrationConfig(api_key='test-key')
        integration = ConfluenceIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = ConfluenceIntegrationConfig(api_key='test-key')
        integration = ConfluenceIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
