"""Tests for token validation."""


from app.validation.token_validator import (
    TokenFieldValidator,
    TokenValidator,
)


class TestTokenValidator:
    """Tests for validator."""

    def test_required(self):
        validator = TokenValidator()
        validator.add_rule('name', TokenFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = TokenValidator()
        validator.add_rule('name', TokenFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = TokenFieldValidator.email('email', 'invalid')
        assert result is not None
        result = TokenFieldValidator.email('email', 'test@example.com')
        assert result is None
