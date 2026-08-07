"""Tests for request validation."""


from app.validation.request_validator import (
    RequestFieldValidator,
    RequestValidator,
)


class TestRequestValidator:
    """Tests for validator."""

    def test_required(self):
        validator = RequestValidator()
        validator.add_rule('name', RequestFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = RequestValidator()
        validator.add_rule('name', RequestFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = RequestFieldValidator.email('email', 'invalid')
        assert result is not None
        result = RequestFieldValidator.email('email', 'test@example.com')
        assert result is None
