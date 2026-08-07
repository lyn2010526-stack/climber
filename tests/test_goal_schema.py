"""Tests for goal schema."""

import pytest
from pydantic import ValidationError

from app.schemas.goal_schema import (
    GoalCreate,
    GoalFilter,
    GoalStatus,
    GoalUpdate,
)


class TestGoalCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = GoalCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            GoalCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            GoalCreate(name='a')

    def test_default_status(self):
        schema = GoalCreate(name='Test')
        assert schema.status == GoalStatus.ACTIVE


class TestGoalUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = GoalUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = GoalUpdate()
        assert schema.name is None


class TestGoalFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = GoalFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = GoalFilter(search='test')
        assert schema.search == 'test'
