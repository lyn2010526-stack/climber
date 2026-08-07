"""Tests for comment schema."""

import pytest
from pydantic import ValidationError

from app.schemas.comment_schema import (
    CommentCreate,
    CommentFilter,
    CommentStatus,
    CommentUpdate,
)


class TestCommentCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = CommentCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            CommentCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            CommentCreate(name='a')

    def test_default_status(self):
        schema = CommentCreate(name='Test')
        assert schema.status == CommentStatus.ACTIVE


class TestCommentUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = CommentUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = CommentUpdate()
        assert schema.name is None


class TestCommentFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = CommentFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = CommentFilter(search='test')
        assert schema.search == 'test'
