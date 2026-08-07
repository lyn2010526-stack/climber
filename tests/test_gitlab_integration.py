"""Tests for gitlab integration."""

import pytest

from app.integrations.gitlab_integration import (
    GitlabIntegration,
    GitlabIntegrationConfig,
)


class TestGitlabIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = GitlabIntegrationConfig(api_key='test-key')
        integration = GitlabIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = GitlabIntegrationConfig(api_key='test-key')
        integration = GitlabIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
