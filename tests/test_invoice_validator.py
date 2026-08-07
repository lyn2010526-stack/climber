"""Tests for invoice validation."""


from app.validation.invoice_validator import (
    InvoiceFieldValidator,
    InvoiceValidator,
)


class TestInvoiceValidator:
    """Tests for validator."""

    def test_required(self):
        validator = InvoiceValidator()
        validator.add_rule('name', InvoiceFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = InvoiceValidator()
        validator.add_rule('name', InvoiceFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = InvoiceFieldValidator.email('email', 'invalid')
        assert result is not None
        result = InvoiceFieldValidator.email('email', 'test@example.com')
        assert result is None
