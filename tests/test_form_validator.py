"""Tests for form validation."""


from app.validation.form_validator import (
    FormFieldValidator,
    FormValidator,
)


class TestFormValidator:
    """Tests for validator."""

    def test_required(self):
        validator = FormValidator()
        validator.add_rule('name', FormFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = FormValidator()
        validator.add_rule('name', FormFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = FormFieldValidator.email('email', 'invalid')
        assert result is not None
        result = FormFieldValidator.email('email', 'test@example.com')
        assert result is None
