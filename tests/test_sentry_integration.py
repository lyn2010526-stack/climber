"""Tests for sentry integration."""

import pytest

from app.integrations.sentry_integration import (
    SentryIntegration,
    SentryIntegrationConfig,
)


class TestSentryIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = SentryIntegrationConfig(api_key='test-key')
        integration = SentryIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = SentryIntegrationConfig(api_key='test-key')
        integration = SentryIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
