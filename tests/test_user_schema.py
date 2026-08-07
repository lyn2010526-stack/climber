"""Tests for user schema."""

import pytest
from pydantic import ValidationError

from app.schemas.user_schema import (
    UserCreate,
    UserFilter,
    UserStatus,
    UserUpdate,
)


class TestUserCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = UserCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            UserCreate(name='a')

    def test_default_status(self):
        schema = UserCreate(name='Test')
        assert schema.status == UserStatus.ACTIVE


class TestUserUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = UserUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = UserUpdate()
        assert schema.name is None


class TestUserFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = UserFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = UserFilter(search='test')
        assert schema.search == 'test'
