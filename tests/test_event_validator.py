"""Tests for event validation."""


from app.validation.event_validator import (
    EventFieldValidator,
    EventValidator,
)


class TestEventValidator:
    """Tests for validator."""

    def test_required(self):
        validator = EventValidator()
        validator.add_rule('name', EventFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = EventValidator()
        validator.add_rule('name', EventFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = EventFieldValidator.email('email', 'invalid')
        assert result is not None
        result = EventFieldValidator.email('email', 'test@example.com')
        assert result is None
