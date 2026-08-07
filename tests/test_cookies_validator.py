"""Tests for cookies validation."""


from app.validation.cookies_validator import (
    CookiesFieldValidator,
    CookiesValidator,
)


class TestCookiesValidator:
    """Tests for validator."""

    def test_required(self):
        validator = CookiesValidator()
        validator.add_rule('name', CookiesFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = CookiesValidator()
        validator.add_rule('name', CookiesFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = CookiesFieldValidator.email('email', 'invalid')
        assert result is not None
        result = CookiesFieldValidator.email('email', 'test@example.com')
        assert result is None
