"""Tests for credentials validation."""


from app.validation.credentials_validator import (
    CredentialsFieldValidator,
    CredentialsValidator,
)


class TestCredentialsValidator:
    """Tests for validator."""

    def test_required(self):
        validator = CredentialsValidator()
        validator.add_rule('name', CredentialsFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = CredentialsValidator()
        validator.add_rule('name', CredentialsFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = CredentialsFieldValidator.email('email', 'invalid')
        assert result is not None
        result = CredentialsFieldValidator.email('email', 'test@example.com')
        assert result is None
