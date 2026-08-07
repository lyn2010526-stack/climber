"""Tests for params validation."""


from app.validation.params_validator import (
    ParamsFieldValidator,
    ParamsValidator,
)


class TestParamsValidator:
    """Tests for validator."""

    def test_required(self):
        validator = ParamsValidator()
        validator.add_rule('name', ParamsFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = ParamsValidator()
        validator.add_rule('name', ParamsFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = ParamsFieldValidator.email('email', 'invalid')
        assert result is not None
        result = ParamsFieldValidator.email('email', 'test@example.com')
        assert result is None
