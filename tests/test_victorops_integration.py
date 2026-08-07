"""Tests for victorops integration."""

import pytest

from app.integrations.victorops_integration import (
    VictoropsIntegration,
    VictoropsIntegrationConfig,
)


class TestVictoropsIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = VictoropsIntegrationConfig(api_key='test-key')
        integration = VictoropsIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = VictoropsIntegrationConfig(api_key='test-key')
        integration = VictoropsIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
