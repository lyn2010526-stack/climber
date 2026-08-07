"""Tests for widget schema."""

import pytest
from pydantic import ValidationError

from app.schemas.widget_schema import (
    WidgetCreate,
    WidgetFilter,
    WidgetStatus,
    WidgetUpdate,
)


class TestWidgetCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = WidgetCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            WidgetCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            WidgetCreate(name='a')

    def test_default_status(self):
        schema = WidgetCreate(name='Test')
        assert schema.status == WidgetStatus.ACTIVE


class TestWidgetUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = WidgetUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = WidgetUpdate()
        assert schema.name is None


class TestWidgetFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = WidgetFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = WidgetFilter(search='test')
        assert schema.search == 'test'
