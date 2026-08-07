"""Tests for kpi schema."""

import pytest
from pydantic import ValidationError

from app.schemas.kpi_schema import (
    KpiCreate,
    KpiFilter,
    KpiStatus,
    KpiUpdate,
)


class TestKpiCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = KpiCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            KpiCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            KpiCreate(name='a')

    def test_default_status(self):
        schema = KpiCreate(name='Test')
        assert schema.status == KpiStatus.ACTIVE


class TestKpiUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = KpiUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = KpiUpdate()
        assert schema.name is None


class TestKpiFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = KpiFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = KpiFilter(search='test')
        assert schema.search == 'test'
