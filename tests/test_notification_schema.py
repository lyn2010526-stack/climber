"""Tests for notification schema."""

import pytest
from pydantic import ValidationError

from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationFilter,
    NotificationStatus,
    NotificationUpdate,
)


class TestNotificationCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = NotificationCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            NotificationCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            NotificationCreate(name='a')

    def test_default_status(self):
        schema = NotificationCreate(name='Test')
        assert schema.status == NotificationStatus.ACTIVE


class TestNotificationUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = NotificationUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = NotificationUpdate()
        assert schema.name is None


class TestNotificationFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = NotificationFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = NotificationFilter(search='test')
        assert schema.search == 'test'
