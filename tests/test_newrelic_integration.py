"""Tests for newrelic integration."""

import pytest

from app.integrations.newrelic_integration import (
    NewrelicIntegration,
    NewrelicIntegrationConfig,
)


class TestNewrelicIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = NewrelicIntegrationConfig(api_key='test-key')
        integration = NewrelicIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = NewrelicIntegrationConfig(api_key='test-key')
        integration = NewrelicIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
