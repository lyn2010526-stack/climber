"""Tests for file validation."""


from app.validation.file_validator import (
    FileFieldValidator,
    FileValidator,
)


class TestFileValidator:
    """Tests for validator."""

    def test_required(self):
        validator = FileValidator()
        validator.add_rule('name', FileFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = FileValidator()
        validator.add_rule('name', FileFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = FileFieldValidator.email('email', 'invalid')
        assert result is not None
        result = FileFieldValidator.email('email', 'test@example.com')
        assert result is None
