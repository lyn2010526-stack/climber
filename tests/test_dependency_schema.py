"""Tests for dependency schema."""

import pytest
from pydantic import ValidationError

from app.schemas.dependency_schema import (
    DependencyCreate,
    DependencyFilter,
    DependencyStatus,
    DependencyUpdate,
)


class TestDependencyCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = DependencyCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            DependencyCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            DependencyCreate(name='a')

    def test_default_status(self):
        schema = DependencyCreate(name='Test')
        assert schema.status == DependencyStatus.ACTIVE


class TestDependencyUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = DependencyUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = DependencyUpdate()
        assert schema.name is None


class TestDependencyFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = DependencyFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = DependencyFilter(search='test')
        assert schema.search == 'test'
