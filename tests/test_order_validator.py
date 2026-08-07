"""Tests for order validation."""


from app.validation.order_validator import (
    OrderFieldValidator,
    OrderValidator,
)


class TestOrderValidator:
    """Tests for validator."""

    def test_required(self):
        validator = OrderValidator()
        validator.add_rule('name', OrderFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = OrderValidator()
        validator.add_rule('name', OrderFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = OrderFieldValidator.email('email', 'invalid')
        assert result is not None
        result = OrderFieldValidator.email('email', 'test@example.com')
        assert result is None
