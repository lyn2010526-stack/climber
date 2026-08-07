"""Tests for risk schema."""

import pytest
from pydantic import ValidationError

from app.schemas.risk_schema import (
    RiskCreate,
    RiskFilter,
    RiskStatus,
    RiskUpdate,
)


class TestRiskCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = RiskCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            RiskCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            RiskCreate(name='a')

    def test_default_status(self):
        schema = RiskCreate(name='Test')
        assert schema.status == RiskStatus.ACTIVE


class TestRiskUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = RiskUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = RiskUpdate()
        assert schema.name is None


class TestRiskFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = RiskFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = RiskFilter(search='test')
        assert schema.search == 'test'
