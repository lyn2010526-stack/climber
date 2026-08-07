"""Tests for github integration."""

import pytest

from app.integrations.github_integration import (
    GithubIntegration,
    GithubIntegrationConfig,
)


class TestGithubIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = GithubIntegrationConfig(api_key='test-key')
        integration = GithubIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = GithubIntegrationConfig(api_key='test-key')
        integration = GithubIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
