"""Tests for notion integration."""

import pytest

from app.integrations.notion_integration import (
    NotionIntegration,
    NotionIntegrationConfig,
)


class TestNotionIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = NotionIntegrationConfig(api_key='test-key')
        integration = NotionIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = NotionIntegrationConfig(api_key='test-key')
        integration = NotionIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
