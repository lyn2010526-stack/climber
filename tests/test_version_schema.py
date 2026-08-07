"""Tests for version schema."""

import pytest
from pydantic import ValidationError

from app.schemas.version_schema import (
    VersionCreate,
    VersionFilter,
    VersionStatus,
    VersionUpdate,
)


class TestVersionCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = VersionCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            VersionCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            VersionCreate(name='a')

    def test_default_status(self):
        schema = VersionCreate(name='Test')
        assert schema.status == VersionStatus.ACTIVE


class TestVersionUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = VersionUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = VersionUpdate()
        assert schema.name is None


class TestVersionFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = VersionFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = VersionFilter(search='test')
        assert schema.search == 'test'
