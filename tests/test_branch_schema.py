"""Tests for branch schema."""

import pytest
from pydantic import ValidationError

from app.schemas.branch_schema import (
    BranchCreate,
    BranchFilter,
    BranchStatus,
    BranchUpdate,
)


class TestBranchCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = BranchCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            BranchCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            BranchCreate(name='a')

    def test_default_status(self):
        schema = BranchCreate(name='Test')
        assert schema.status == BranchStatus.ACTIVE


class TestBranchUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = BranchUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = BranchUpdate()
        assert schema.name is None


class TestBranchFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = BranchFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = BranchFilter(search='test')
        assert schema.search == 'test'
