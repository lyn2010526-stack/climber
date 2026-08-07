"""Tests for preferences validation."""


from app.validation.preferences_validator import (
    PreferencesFieldValidator,
    PreferencesValidator,
)


class TestPreferencesValidator:
    """Tests for validator."""

    def test_required(self):
        validator = PreferencesValidator()
        validator.add_rule('name', PreferencesFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = PreferencesValidator()
        validator.add_rule('name', PreferencesFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = PreferencesFieldValidator.email('email', 'invalid')
        assert result is not None
        result = PreferencesFieldValidator.email('email', 'test@example.com')
        assert result is None
