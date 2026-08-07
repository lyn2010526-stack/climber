"""Tests for subscription validation."""


from app.validation.subscription_validator import (
    SubscriptionFieldValidator,
    SubscriptionValidator,
)


class TestSubscriptionValidator:
    """Tests for validator."""

    def test_required(self):
        validator = SubscriptionValidator()
        validator.add_rule('name', SubscriptionFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = SubscriptionValidator()
        validator.add_rule('name', SubscriptionFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = SubscriptionFieldValidator.email('email', 'invalid')
        assert result is not None
        result = SubscriptionFieldValidator.email('email', 'test@example.com')
        assert result is None
