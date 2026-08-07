"""Tests for twilio integration."""

import pytest

from app.integrations.twilio_integration import (
    TwilioIntegration,
    TwilioIntegrationConfig,
)


class TestTwilioIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = TwilioIntegrationConfig(api_key='test-key')
        integration = TwilioIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = TwilioIntegrationConfig(api_key='test-key')
        integration = TwilioIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
