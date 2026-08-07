"""Tests for response validation."""


from app.validation.response_validator import (
    ResponseFieldValidator,
    ResponseValidator,
)


class TestResponseValidator:
    """Tests for validator."""

    def test_required(self):
        validator = ResponseValidator()
        validator.add_rule('name', ResponseFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = ResponseValidator()
        validator.add_rule('name', ResponseFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = ResponseFieldValidator.email('email', 'invalid')
        assert result is not None
        result = ResponseFieldValidator.email('email', 'test@example.com')
        assert result is None
