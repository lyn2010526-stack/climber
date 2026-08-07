"""Tests for asana integration."""

import pytest

from app.integrations.asana_integration import (
    AsanaIntegration,
    AsanaIntegrationConfig,
)


class TestAsanaIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = AsanaIntegrationConfig(api_key='test-key')
        integration = AsanaIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = AsanaIntegrationConfig(api_key='test-key')
        integration = AsanaIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
