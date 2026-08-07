"""Tests for metric schema."""

import pytest
from pydantic import ValidationError

from app.schemas.metric_schema import (
    MetricCreate,
    MetricFilter,
    MetricStatus,
    MetricUpdate,
)


class TestMetricCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = MetricCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            MetricCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            MetricCreate(name='a')

    def test_default_status(self):
        schema = MetricCreate(name='Test')
        assert schema.status == MetricStatus.ACTIVE


class TestMetricUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = MetricUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = MetricUpdate()
        assert schema.name is None


class TestMetricFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = MetricFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = MetricFilter(search='test')
        assert schema.search == 'test'
