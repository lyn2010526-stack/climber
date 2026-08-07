"""Tests for mailchimp integration."""

import pytest

from app.integrations.mailchimp_integration import (
    MailchimpIntegration,
    MailchimpIntegrationConfig,
)


class TestMailchimpIntegration:
    """Tests for integration."""

    @pytest.mark.asyncio
    async def test_connect(self):
        config = MailchimpIntegrationConfig(api_key='test-key')
        integration = MailchimpIntegration(config=config)
        result = await integration.connect()
        assert result is True
        assert integration.is_connected() is True

    @pytest.mark.asyncio
    async def test_sync(self):
        config = MailchimpIntegrationConfig(api_key='test-key')
        integration = MailchimpIntegration(config=config)
        await integration.connect()
        result = await integration.sync()
        assert result.success is True
