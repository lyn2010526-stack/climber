"""Tests for session validation."""


from app.validation.session_validator import (
    SessionFieldValidator,
    SessionValidator,
)


class TestSessionValidator:
    """Tests for validator."""

    def test_required(self):
        validator = SessionValidator()
        validator.add_rule('name', SessionFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = SessionValidator()
        validator.add_rule('name', SessionFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = SessionFieldValidator.email('email', 'invalid')
        assert result is not None
        result = SessionFieldValidator.email('email', 'test@example.com')
        assert result is None
