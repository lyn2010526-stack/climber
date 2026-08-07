"""Tests for team schema."""

import pytest
from pydantic import ValidationError

from app.schemas.team_schema import (
    TeamCreate,
    TeamFilter,
    TeamStatus,
    TeamUpdate,
)


class TestTeamCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = TeamCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            TeamCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            TeamCreate(name='a')

    def test_default_status(self):
        schema = TeamCreate(name='Test')
        assert schema.status == TeamStatus.ACTIVE


class TestTeamUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = TeamUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = TeamUpdate()
        assert schema.name is None


class TestTeamFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = TeamFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = TeamFilter(search='test')
        assert schema.search == 'test'
