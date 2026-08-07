"""Tests for download validation."""


from app.validation.download_validator import (
    DownloadFieldValidator,
    DownloadValidator,
)


class TestDownloadValidator:
    """Tests for validator."""

    def test_required(self):
        validator = DownloadValidator()
        validator.add_rule('name', DownloadFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = DownloadValidator()
        validator.add_rule('name', DownloadFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = DownloadFieldValidator.email('email', 'invalid')
        assert result is not None
        result = DownloadFieldValidator.email('email', 'test@example.com')
        assert result is None
