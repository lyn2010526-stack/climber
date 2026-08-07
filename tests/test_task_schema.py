"""Tests for task schema."""

import pytest
from pydantic import ValidationError

from app.schemas.task_schema import (
    TaskCreate,
    TaskFilter,
    TaskStatus,
    TaskUpdate,
)


class TestTaskCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = TaskCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            TaskCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            TaskCreate(name='a')

    def test_default_status(self):
        schema = TaskCreate(name='Test')
        assert schema.status == TaskStatus.ACTIVE


class TestTaskUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = TaskUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = TaskUpdate()
        assert schema.name is None


class TestTaskFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = TaskFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = TaskFilter(search='test')
        assert schema.search == 'test'
