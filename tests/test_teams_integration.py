"""Tests for teams integration."""


from app.integrations.teams_integration import (
    TeamsConfig,
    TeamsIntegration,
    TeamsWebhook,
)


class TestTeamsIntegration:
    """Tests for integration."""

    def test_create_integration(self):
        config = TeamsConfig(base_url='https://api.example.com')
        integration = TeamsIntegration(config=config)
        assert integration.config.base_url == 'https://api.example.com'

    def test_register_webhook(self):
        integration = TeamsIntegration()
        webhook = TeamsWebhook(id='wh_1', url='https://example.com/hook')
        integration.register_webhook(webhook)
        assert 'wh_1' in integration._webhooks

    def test_verify_webhook_signature(self):
        integration = TeamsIntegration()
        payload = b'{"event": "test"}'
        import hashlib
        import hmac
        secret = 'test_secret'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert integration.verify_webhook_signature(payload, sig, secret)

    def test_get_stats(self):
        integration = TeamsIntegration()
        stats = integration.get_stats()
        assert stats['total_requests'] == 0
