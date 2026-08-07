"""Tests for elastic integration."""

import pytest

from app.integrations.elastic_integration import (
    ElasticIntegration,
    ElasticIntegrationConfig,
)


class TestElasticIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = ElasticIntegrationConfig(api_key='test-key')
        integration = ElasticIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = ElasticIntegrationConfig(api_key='test-key')
        integration = ElasticIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
