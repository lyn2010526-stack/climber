"""Tests for analytics schema."""

import pytest
from pydantic import ValidationError

from app.schemas.analytics_schema import (
    AnalyticsCreate,
    AnalyticsFilter,
    AnalyticsStatus,
    AnalyticsUpdate,
)


class TestAnalyticsCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = AnalyticsCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            AnalyticsCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            AnalyticsCreate(name='a')

    def test_default_status(self):
        schema = AnalyticsCreate(name='Test')
        assert schema.status == AnalyticsStatus.ACTIVE


class TestAnalyticsUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = AnalyticsUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = AnalyticsUpdate()
        assert schema.name is None


class TestAnalyticsFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = AnalyticsFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = AnalyticsFilter(search='test')
        assert schema.search == 'test'
