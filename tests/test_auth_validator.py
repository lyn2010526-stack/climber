"""Tests for auth validation."""


from app.validation.auth_validator import (
    AuthFieldValidator,
    AuthValidator,
)


class TestAuthValidator:
    """Tests for validator."""

    def test_required(self):
        validator = AuthValidator()
        validator.add_rule('name', AuthFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = AuthValidator()
        validator.add_rule('name', AuthFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = AuthFieldValidator.email('email', 'invalid')
        assert result is not None
        result = AuthFieldValidator.email('email', 'test@example.com')
        assert result is None
