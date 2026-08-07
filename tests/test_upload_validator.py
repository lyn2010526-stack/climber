"""Tests for upload validation."""


from app.validation.upload_validator import (
    UploadFieldValidator,
    UploadValidator,
)


class TestUploadValidator:
    """Tests for validator."""

    def test_required(self):
        validator = UploadValidator()
        validator.add_rule('name', UploadFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = UploadValidator()
        validator.add_rule('name', UploadFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = UploadFieldValidator.email('email', 'invalid')
        assert result is not None
        result = UploadFieldValidator.email('email', 'test@example.com')
        assert result is None
