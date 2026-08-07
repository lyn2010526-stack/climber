"""Tests for project schema."""

import pytest
from pydantic import ValidationError

from app.schemas.project_schema import (
    ProjectCreate,
    ProjectFilter,
    ProjectStatus,
    ProjectUpdate,
)


class TestProjectCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = ProjectCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name='a')

    def test_default_status(self):
        schema = ProjectCreate(name='Test')
        assert schema.status == ProjectStatus.ACTIVE


class TestProjectUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = ProjectUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = ProjectUpdate()
        assert schema.name is None


class TestProjectFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = ProjectFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = ProjectFilter(search='test')
        assert schema.search == 'test'
