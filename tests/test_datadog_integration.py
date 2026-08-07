"""Tests for datadog integration."""

import pytest

from app.integrations.datadog_integration import (
    DatadogIntegration,
    DatadogIntegrationConfig,
)


class TestDatadogIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = DatadogIntegrationConfig(api_key='test-key')
        integration = DatadogIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = DatadogIntegrationConfig(api_key='test-key')
        integration = DatadogIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
