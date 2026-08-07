"""Tests for schema validation."""


from app.validation.schema_validator import (
    SchemaFieldValidator,
    SchemaValidator,
)


class TestSchemaValidator:
    """Tests for validator."""

    def test_required(self):
        validator = SchemaValidator()
        validator.add_rule('name', SchemaFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = SchemaValidator()
        validator.add_rule('name', SchemaFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = SchemaFieldValidator.email('email', 'invalid')
        assert result is not None
        result = SchemaFieldValidator.email('email', 'test@example.com')
        assert result is None
