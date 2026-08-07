"""Tests for report schema."""

import pytest
from pydantic import ValidationError

from app.schemas.report_schema import (
    ReportCreate,
    ReportFilter,
    ReportStatus,
    ReportUpdate,
)


class TestReportCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ReportCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ReportCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ReportCreate(name='a')

    def test_default_status(self):
        schema = ReportCreate(name='Test')
        assert schema.status == ReportStatus.ACTIVE


class TestReportUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ReportUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ReportUpdate()
        assert schema.name is None


class TestReportFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ReportFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ReportFilter(search='test')
        assert schema.search == 'test'
