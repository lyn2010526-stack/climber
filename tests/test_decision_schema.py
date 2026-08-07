"""Tests for decision schema."""

import pytest
from pydantic import ValidationError

from app.schemas.decision_schema import (
    DecisionCreate,
    DecisionFilter,
    DecisionStatus,
    DecisionUpdate,
)


class TestDecisionCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = DecisionCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            DecisionCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            DecisionCreate(name='a')

    def test_default_status(self):
        schema = DecisionCreate(name='Test')
        assert schema.status == DecisionStatus.ACTIVE


class TestDecisionUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = DecisionUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = DecisionUpdate()
        assert schema.name is None


class TestDecisionFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = DecisionFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = DecisionFilter(search='test')
        assert schema.search == 'test'
