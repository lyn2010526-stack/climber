"""Tests for opsgenie integration."""

import pytest

from app.integrations.opsgenie_integration import (
    OpsgenieIntegration,
    OpsgenieIntegrationConfig,
)


class TestOpsgenieIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = OpsgenieIntegrationConfig(api_key='test-key')
        integration = OpsgenieIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = OpsgenieIntegrationConfig(api_key='test-key')
        integration = OpsgenieIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
