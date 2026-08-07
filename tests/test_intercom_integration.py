"""Tests for intercom integration."""

import pytest

from app.integrations.intercom_integration import (
    IntercomIntegration,
    IntercomIntegrationConfig,
)


class TestIntercomIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = IntercomIntegrationConfig(api_key='test-key')
        integration = IntercomIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = IntercomIntegrationConfig(api_key='test-key')
        integration = IntercomIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
