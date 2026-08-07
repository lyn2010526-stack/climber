"""Tests for zendesk integration."""


from app.integrations.zendesk_integration import (
    ZendeskConfig,
    ZendeskIntegration,
    ZendeskWebhook,
)


class TestZendeskIntegration:
    """Tests for integration."""

    def test_create_integration(self):
        config = ZendeskConfig(base_url='https://api.example.com')
        integration = ZendeskIntegration(config=config)
        assert integration.config.base_url == 'https://api.example.com'

    def test_register_webhook(self):
        integration = ZendeskIntegration()
        webhook = ZendeskWebhook(id='wh_1', url='https://example.com/hook')
        integration.register_webhook(webhook)
        assert 'wh_1' in integration._webhooks

    def test_verify_webhook_signature(self):
        integration = ZendeskIntegration()
        payload = b'{"event": "test"}'
        import hashlib
        import hmac
        secret = 'test_secret'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert integration.verify_webhook_signature(payload, sig, secret)

    def test_get_stats(self):
        integration = ZendeskIntegration()
        stats = integration.get_stats()
        assert stats['total_requests'] == 0
