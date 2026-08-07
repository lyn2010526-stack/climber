"""Tests for payload validation."""


from app.validation.payload_validator import (
    PayloadFieldValidator,
    PayloadValidator,
)


class TestPayloadValidator:
    """Tests for validator."""

    def test_required(self):
        validator = PayloadValidator()
        validator.add_rule('name', PayloadFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = PayloadValidator()
        validator.add_rule('name', PayloadFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = PayloadFieldValidator.email('email', 'invalid')
        assert result is not None
        result = PayloadFieldValidator.email('email', 'test@example.com')
        assert result is None
