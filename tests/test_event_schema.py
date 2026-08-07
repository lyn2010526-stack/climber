"""Tests for event schema."""

import pytest
from pydantic import ValidationError

from app.schemas.event_schema import (
    EventCreate,
    EventFilter,
    EventStatus,
    EventUpdate,
)


class TestEventCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = EventCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            EventCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            EventCreate(name='a')

    def test_default_status(self):
        schema = EventCreate(name='Test')
        assert schema.status == EventStatus.ACTIVE


class TestEventUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = EventUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = EventUpdate()
        assert schema.name is None


class TestEventFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = EventFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = EventFilter(search='test')
        assert schema.search == 'test'
