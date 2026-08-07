"""Tests for zapier integration."""

import pytest

from app.integrations.zapier_integration import (
    ZapierIntegration,
    ZapierIntegrationConfig,
)


class TestZapierIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = ZapierIntegrationConfig(api_key='test-key')
        integration = ZapierIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = ZapierIntegrationConfig(api_key='test-key')
        integration = ZapierIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
