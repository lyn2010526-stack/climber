"""Tests for shopify integration."""


from app.integrations.shopify_integration import (
    ShopifyConfig,
    ShopifyIntegration,
    ShopifyWebhook,
)


class TestShopifyIntegration:
    """Tests for integration."""

    def test_create_integration(self):
        config = ShopifyConfig(base_url='https://api.example.com')
        integration = ShopifyIntegration(config=config)
        assert integration.config.base_url == 'https://api.example.com'

    def test_register_webhook(self):
        integration = ShopifyIntegration()
        webhook = ShopifyWebhook(id='wh_1', url='https://example.com/hook')
        integration.register_webhook(webhook)
        assert 'wh_1' in integration._webhooks

    def test_verify_webhook_signature(self):
        integration = ShopifyIntegration()
        payload = b'{"event": "test"}'
        import hashlib
        import hmac
        secret = 'test_secret'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert integration.verify_webhook_signature(payload, sig, secret)

    def test_get_stats(self):
        integration = ShopifyIntegration()
        stats = integration.get_stats()
        assert stats['total_requests'] == 0
