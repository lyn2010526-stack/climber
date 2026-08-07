"""Tests for profile validation."""


from app.validation.profile_validator import (
    ProfileFieldValidator,
    ProfileValidator,
)


class TestProfileValidator:
    """Tests for validator."""

    def test_required(self):
        validator = ProfileValidator()
        validator.add_rule('name', ProfileFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = ProfileValidator()
        validator.add_rule('name', ProfileFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = ProfileFieldValidator.email('email', 'invalid')
        assert result is not None
        result = ProfileFieldValidator.email('email', 'test@example.com')
        assert result is None
