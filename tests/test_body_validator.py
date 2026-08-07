"""Tests for body validation."""


from app.validation.body_validator import (
    BodyFieldValidator,
    BodyValidator,
)


class TestBodyValidator:
    """Tests for validator."""

    def test_required(self):
        validator = BodyValidator()
        validator.add_rule('name', BodyFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = BodyValidator()
        validator.add_rule('name', BodyFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = BodyFieldValidator.email('email', 'invalid')
        assert result is not None
        result = BodyFieldValidator.email('email', 'test@example.com')
        assert result is None
