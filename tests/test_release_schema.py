"""Tests for release schema."""

import pytest
from pydantic import ValidationError

from app.schemas.release_schema import (
    ReleaseCreate,
    ReleaseFilter,
    ReleaseStatus,
    ReleaseUpdate,
)


class TestReleaseCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ReleaseCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ReleaseCreate(name='a')

    def test_default_status(self):
        schema = ReleaseCreate(name='Test')
        assert schema.status == ReleaseStatus.ACTIVE


class TestReleaseUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ReleaseUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ReleaseUpdate()
        assert schema.name is None


class TestReleaseFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ReleaseFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ReleaseFilter(search='test')
        assert schema.search == 'test'
