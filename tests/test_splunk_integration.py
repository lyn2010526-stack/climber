"""Tests for splunk integration."""

import pytest

from app.integrations.splunk_integration import (
    SplunkIntegration,
    SplunkIntegrationConfig,
)


class TestSplunkIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = SplunkIntegrationConfig(api_key='test-key')
        integration = SplunkIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = SplunkIntegrationConfig(api_key='test-key')
        integration = SplunkIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
