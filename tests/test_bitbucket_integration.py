"""Tests for bitbucket integration."""

import pytest

from app.integrations.bitbucket_integration import (
    BitbucketIntegration,
    BitbucketIntegrationConfig,
)


class TestBitbucketIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = BitbucketIntegrationConfig(api_key='test-key')
        integration = BitbucketIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = BitbucketIntegrationConfig(api_key='test-key')
        integration = BitbucketIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
