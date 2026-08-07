"""Tests for salesforce integration."""

import pytest

from app.integrations.salesforce_integration import (
    SalesforceIntegration,
    SalesforceIntegrationConfig,
)


class TestSalesforceIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = SalesforceIntegrationConfig(api_key='test-key')
        integration = SalesforceIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = SalesforceIntegrationConfig(api_key='test-key')
        integration = SalesforceIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
