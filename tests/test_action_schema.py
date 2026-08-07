"""Tests for action schema."""

import pytest
from pydantic import ValidationError

from app.schemas.action_schema import (
    ActionCreate,
    ActionFilter,
    ActionStatus,
    ActionUpdate,
)


class TestActionCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ActionCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ActionCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ActionCreate(name='a')

    def test_default_status(self):
        schema = ActionCreate(name='Test')
        assert schema.status == ActionStatus.ACTIVE


class TestActionUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ActionUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ActionUpdate()
        assert schema.name is None


class TestActionFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ActionFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ActionFilter(search='test')
        assert schema.search == 'test'
