"""Tests for aws_s3 integration."""


from app.integrations.aws_s3_integration import (
    AwsS3Config,
    AwsS3Integration,
    AwsS3Webhook,
)


class TestAwsS3Integration:
    """Tests for integration."""

    def test_create_integration(self):
        config = AwsS3Config(base_url='https://api.example.com')
        integration = AwsS3Integration(config=config)
        assert integration.config.base_url == 'https://api.example.com'

    def test_register_webhook(self):
        integration = AwsS3Integration()
        webhook = AwsS3Webhook(id='wh_1', url='https://example.com/hook')
        integration.register_webhook(webhook)
        assert 'wh_1' in integration._webhooks

    def test_verify_webhook_signature(self):
        integration = AwsS3Integration()
        payload = b'{"event": "test"}'
        import hashlib
        import hmac
        secret = 'test_secret'
        sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert integration.verify_webhook_signature(payload, sig, secret)

    def test_get_stats(self):
        integration = AwsS3Integration()
        stats = integration.get_stats()
        assert stats['total_requests'] == 0
