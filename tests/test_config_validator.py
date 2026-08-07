"""Tests for config validation."""


from app.validation.config_validator import (
    ConfigFieldValidator,
    ConfigValidator,
)


class TestConfigValidator:
    """Tests for validator."""

    def test_required(self):
        validator = ConfigValidator()
        validator.add_rule('name', ConfigFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = ConfigValidator()
        validator.add_rule('name', ConfigFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = ConfigFieldValidator.email('email', 'invalid')
        assert result is not None
        result = ConfigFieldValidator.email('email', 'test@example.com')
        assert result is None
