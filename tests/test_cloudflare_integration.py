"""Tests for cloudflare integration."""

import pytest

from app.integrations.cloudflare_integration import (
    CloudflareIntegration,
    CloudflareIntegrationConfig,
)


class TestCloudflareIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = CloudflareIntegrationConfig(api_key='test-key')
        integration = CloudflareIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = CloudflareIntegrationConfig(api_key='test-key')
        integration = CloudflareIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
