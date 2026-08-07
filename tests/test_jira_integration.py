"""Tests for jira integration."""

import pytest

from app.integrations.jira_integration import (
    JiraIntegration,
    JiraIntegrationConfig,
)


class TestJiraIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = JiraIntegrationConfig(api_key='test-key')
        integration = JiraIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = JiraIntegrationConfig(api_key='test-key')
        integration = JiraIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
