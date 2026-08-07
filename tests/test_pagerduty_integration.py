"""Tests for pagerduty integration."""

import pytest

from app.integrations.pagerduty_integration import (
    PagerdutyIntegration,
    PagerdutyIntegrationConfig,
)


class TestPagerdutyIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = PagerdutyIntegrationConfig(api_key='test-key')
        integration = PagerdutyIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = PagerdutyIntegrationConfig(api_key='test-key')
        integration = PagerdutyIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
