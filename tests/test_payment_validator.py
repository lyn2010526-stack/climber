"""Tests for payment validation."""


from app.validation.payment_validator import (
    PaymentFieldValidator,
    PaymentValidator,
)


class TestPaymentValidator:
    """Tests for validator."""

    def test_required(self):
        validator = PaymentValidator()
        validator.add_rule('name', PaymentFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = PaymentValidator()
        validator.add_rule('name', PaymentFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = PaymentFieldValidator.email('email', 'invalid')
        assert result is not None
        result = PaymentFieldValidator.email('email', 'test@example.com')
        assert result is None
