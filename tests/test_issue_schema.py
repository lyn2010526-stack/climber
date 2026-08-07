"""Tests for issue schema."""

import pytest
from pydantic import ValidationError

from app.schemas.issue_schema import (
    IssueCreate,
    IssueFilter,
    IssueStatus,
    IssueUpdate,
)


class TestIssueCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = IssueCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            IssueCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            IssueCreate(name='a')

    def test_default_status(self):
        schema = IssueCreate(name='Test')
        assert schema.status == IssueStatus.ACTIVE


class TestIssueUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = IssueUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = IssueUpdate()
        assert schema.name is None


class TestIssueFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = IssueFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = IssueFilter(search='test')
        assert schema.search == 'test'
