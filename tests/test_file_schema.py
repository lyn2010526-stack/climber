"""Tests for file schema."""

import pytest
from pydantic import ValidationError

from app.schemas.file_schema import (
    FileCreate,
    FileFilter,
    FileStatus,
    FileUpdate,
)


class TestFileCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = FileCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            FileCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            FileCreate(name='a')

    def test_default_status(self):
        schema = FileCreate(name='Test')
        assert schema.status == FileStatus.ACTIVE


class TestFileUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = FileUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = FileUpdate()
        assert schema.name is None


class TestFileFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = FileFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = FileFilter(search='test')
        assert schema.search == 'test'
