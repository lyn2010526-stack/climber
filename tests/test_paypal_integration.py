"""Tests for paypal integration."""

import pytest

from app.integrations.paypal_integration import (
    PaypalIntegration,
    PaypalIntegrationConfig,
)


class TestPaypalIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = PaypalIntegrationConfig(api_key='test-key')
        integration = PaypalIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = PaypalIntegrationConfig(api_key='test-key')
        integration = PaypalIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
