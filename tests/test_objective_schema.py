"""Tests for objective schema."""

import pytest
from pydantic import ValidationError

from app.schemas.objective_schema import (
    ObjectiveCreate,
    ObjectiveFilter,
    ObjectiveStatus,
    ObjectiveUpdate,
)


class TestObjectiveCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ObjectiveCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ObjectiveCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ObjectiveCreate(name='a')

    def test_default_status(self):
        schema = ObjectiveCreate(name='Test')
        assert schema.status == ObjectiveStatus.ACTIVE


class TestObjectiveUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ObjectiveUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ObjectiveUpdate()
        assert schema.name is None


class TestObjectiveFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ObjectiveFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ObjectiveFilter(search='test')
        assert schema.search == 'test'
