"""Tests for message schema."""

import pytest
from pydantic import ValidationError

from app.schemas.message_schema import (
    MessageCreate,
    MessageFilter,
    MessageStatus,
    MessageUpdate,
)


class TestMessageCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = MessageCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            MessageCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            MessageCreate(name='a')

    def test_default_status(self):
        schema = MessageCreate(name='Test')
        assert schema.status == MessageStatus.ACTIVE


class TestMessageUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = MessageUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = MessageUpdate()
        assert schema.name is None


class TestMessageFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = MessageFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = MessageFilter(search='test')
        assert schema.search == 'test'
