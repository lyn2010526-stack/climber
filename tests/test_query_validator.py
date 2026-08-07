"""Tests for query validation."""


from app.validation.query_validator import (
    QueryFieldValidator,
    QueryValidator,
)


class TestQueryValidator:
    """Tests for validator."""

    def test_required(self):
        validator = QueryValidator()
        validator.add_rule('name', QueryFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = QueryValidator()
        validator.add_rule('name', QueryFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = QueryFieldValidator.email('email', 'invalid')
        assert result is not None
        result = QueryFieldValidator.email('email', 'test@example.com')
        assert result is None
