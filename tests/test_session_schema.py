"""Tests for session schema."""

import pytest
from pydantic import ValidationError

from app.schemas.session_schema import (
    SessionCreate,
    SessionFilter,
    SessionStatus,
    SessionUpdate,
)


class TestSessionCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = SessionCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            SessionCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            SessionCreate(name='a')

    def test_default_status(self):
        schema = SessionCreate(name='Test')
        assert schema.status == SessionStatus.ACTIVE


class TestSessionUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = SessionUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = SessionUpdate()
        assert schema.name is None


class TestSessionFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = SessionFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = SessionFilter(search='test')
        assert schema.search == 'test'
