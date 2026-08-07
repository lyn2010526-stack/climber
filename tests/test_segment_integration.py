"""Tests for segment integration."""

import pytest

from app.integrations.segment_integration import (
    SegmentIntegration,
    SegmentIntegrationConfig,
)


class TestSegmentIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = SegmentIntegrationConfig(api_key='test-key')
        integration = SegmentIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = SegmentIntegrationConfig(api_key='test-key')
        integration = SegmentIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
