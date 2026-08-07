"""Tests for headers validation."""


from app.validation.headers_validator import (
    HeadersFieldValidator,
    HeadersValidator,
)


class TestHeadersValidator:
    """Tests for validator."""

    def test_required(self):
        validator = HeadersValidator()
        validator.add_rule('name', HeadersFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = HeadersValidator()
        validator.add_rule('name', HeadersFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = HeadersFieldValidator.email('email', 'invalid')
        assert result is not None
        result = HeadersFieldValidator.email('email', 'test@example.com')
        assert result is None
