"""Tests for initiative schema."""

import pytest
from pydantic import ValidationError

from app.schemas.initiative_schema import (
    InitiativeCreate,
    InitiativeFilter,
    InitiativeStatus,
    InitiativeUpdate,
)


class TestInitiativeCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = InitiativeCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            InitiativeCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            InitiativeCreate(name='a')

    def test_default_status(self):
        schema = InitiativeCreate(name='Test')
        assert schema.status == InitiativeStatus.ACTIVE


class TestInitiativeUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = InitiativeUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = InitiativeUpdate()
        assert schema.name is None


class TestInitiativeFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = InitiativeFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = InitiativeFilter(search='test')
        assert schema.search == 'test'
