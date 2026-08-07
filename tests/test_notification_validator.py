"""Tests for notification validation."""


from app.validation.notification_validator import (
    NotificationFieldValidator,
    NotificationValidator,
)


class TestNotificationValidator:
    """Tests for validator."""

    def test_required(self):
        validator = NotificationValidator()
        validator.add_rule('name', NotificationFieldValidator.required)
        result = validator.validate({'name': ''})
        assert result.valid is False
        assert len(result.errors) == 1

    def test_valid(self):
        validator = NotificationValidator()
        validator.add_rule('name', NotificationFieldValidator.required)
        result = validator.validate({'name': 'Test'})
        assert result.valid is True

    def test_email(self):
        result = NotificationFieldValidator.email('email', 'invalid')
        assert result is not None
        result = NotificationFieldValidator.email('email', 'test@example.com')
        assert result is None
