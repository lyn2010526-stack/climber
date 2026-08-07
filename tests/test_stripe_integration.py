"""Tests for stripe integration."""

import pytest

from app.integrations.stripe_integration import (
    StripeIntegration,
    StripeIntegrationConfig,
)


class TestStripeIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = StripeIntegrationConfig(api_key='test-key')
        integration = StripeIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = StripeIntegrationConfig(api_key='test-key')
        integration = StripeIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
