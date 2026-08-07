"""Tests for blocker schema."""

import pytest
from pydantic import ValidationError

from app.schemas.blocker_schema import (
    BlockerCreate,
    BlockerFilter,
    BlockerStatus,
    BlockerUpdate,
)


class TestBlockerCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = BlockerCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            BlockerCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            BlockerCreate(name='a')

    def test_default_status(self):
        schema = BlockerCreate(name='Test')
        assert schema.status == BlockerStatus.ACTIVE


class TestBlockerUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = BlockerUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = BlockerUpdate()
        assert schema.name is None


class TestBlockerFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = BlockerFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = BlockerFilter(search='test')
        assert schema.search == 'test'
