"""Tests for webhook validation."""


from app.validation.webhook_validator import (
    WebhookFieldValidator,
    WebhookValidator,
)


class TestWebhookValidator:
    """Tests for validator."""

    def test_required(self):
        validator = WebhookValidator()
        validator.add_rule('name', WebhookFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = WebhookValidator()
        validator.add_rule('name', WebhookFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = WebhookFieldValidator.email('email', 'invalid')
        assert result is not None
        result = WebhookFieldValidator.email('email', 'test@example.com')
        assert result is None
