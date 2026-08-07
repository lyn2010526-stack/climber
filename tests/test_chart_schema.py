"""Tests for chart schema."""

import pytest
from pydantic import ValidationError

from app.schemas.chart_schema import (
    ChartCreate,
    ChartFilter,
    ChartStatus,
    ChartUpdate,
)


class TestChartCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ChartCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ChartCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ChartCreate(name='a')

    def test_default_status(self):
        schema = ChartCreate(name='Test')
        assert schema.status == ChartStatus.ACTIVE


class TestChartUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ChartUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ChartUpdate()
        assert schema.name is None


class TestChartFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ChartFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ChartFilter(search='test')
        assert schema.search == 'test'
