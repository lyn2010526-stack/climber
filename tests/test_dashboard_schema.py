"""Tests for dashboard schema."""

import pytest
from pydantic import ValidationError

from app.schemas.dashboard_schema import (
    DashboardCreate,
    DashboardFilter,
    DashboardStatus,
    DashboardUpdate,
)


class TestDashboardCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = DashboardCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            DashboardCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            DashboardCreate(name='a')

    def test_default_status(self):
        schema = DashboardCreate(name='Test')
        assert schema.status == DashboardStatus.ACTIVE


class TestDashboardUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = DashboardUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = DashboardUpdate()
        assert schema.name is None


class TestDashboardFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = DashboardFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = DashboardFilter(search='test')
        assert schema.search == 'test'
