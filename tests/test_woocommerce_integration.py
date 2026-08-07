"""Tests for woocommerce integration."""


from app.integrations.woocommerce_integration import (
    WoocommerceConfig,
    WoocommerceIntegration,
    WoocommerceWebhook,
)


class TestWoocommerceIntegration:
    """Tests for integration."""

    def test_create_integration(self):
        config = WoocommerceConfig(base_url='https://api.example.com')
        integration = WoocommerceIntegration(config=config)
        assert integration.config.base_url == 'https://api.example.com'

    def test_register_webhook(self):
        integration = WoocommerceIntegration()
        webhook = WoocommerceWebhook(id='wh_1', url='https://example.com/hook')
        integration.register_webhook(webhook)
        assert 'wh_1' in integration._webhooks

    def test_verify_webhook_signature(self):
        integration = WoocommerceIntegration()
        payload = b'{"event": "test"}'
        import hashlib
        import hmac
        secret = 'test_secret'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert integration.verify_webhook_signature(payload, sig, secret)

    def test_get_stats(self):
        integration = WoocommerceIntegration()
        stats = integration.get_stats()
        assert stats['total_requests'] == 0
