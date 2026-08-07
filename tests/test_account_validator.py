"""Tests for account validation."""


from app.validation.account_validator import (
    AccountFieldValidator,
    AccountValidator,
)


class TestAccountValidator:
    """Tests for validator."""

    def test_required(self):
        validator = AccountValidator()
        validator.add_rule('name', AccountFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = AccountValidator()
        validator.add_rule('name', AccountFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = AccountFieldValidator.email('email', 'invalid')
        assert result is not None
        result = AccountFieldValidator.email('email', 'test@example.com')
        assert result is None
