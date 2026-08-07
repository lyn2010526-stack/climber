"""Tests for input validation."""


from app.validation.input_validator import (
    InputFieldValidator,
    InputValidator,
)


class TestInputValidator:
    """Tests for validator."""

    def test_required(self):
        validator = InputValidator()
        validator.add_rule('name', InputFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = InputValidator()
        validator.add_rule('name', InputFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = InputFieldValidator.email('email', 'invalid')
        assert result is not None
        result = InputFieldValidator.email('email', 'test@example.com')
        assert result is None
