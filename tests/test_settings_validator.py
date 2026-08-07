"""Tests for settings validation."""


from app.validation.settings_validator import (
    SettingsFieldValidator,
    SettingsValidator,
)


class TestSettingsValidator:
    """Tests for validator."""

    def test_required(self):
        validator = SettingsValidator()
        validator.add_rule('name', SettingsFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = SettingsValidator()
        validator.add_rule('name', SettingsFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = SettingsFieldValidator.email('email', 'invalid')
        assert result is not None
        result = SettingsFieldValidator.email('email', 'test@example.com')
        assert result is None
