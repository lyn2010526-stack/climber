"""Tests for figma integration."""

import pytest

from app.integrations.figma_integration import (
    FigmaIntegration,
    FigmaIntegrationConfig,
)


class TestFigmaIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = FigmaIntegrationConfig(api_key='test-key')
        integration = FigmaIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = FigmaIntegrationConfig(api_key='test-key')
        integration = FigmaIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
