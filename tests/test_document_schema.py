"""Tests for document schema."""

import pytest
from pydantic import ValidationError

from app.schemas.document_schema import (
    DocumentCreate,
    DocumentFilter,
    DocumentStatus,
    DocumentUpdate,
)


class TestDocumentCreate:
    """Tests for create schema."""

    def test_valid_create(self):
        data = {'name': 'Test Item'}
        schema = DocumentCreate(**data)
        assert schema.name == 'Test Item'

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            DocumentCreate(name='')

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            DocumentCreate(name='a')

    def test_default_status(self):
        schema = DocumentCreate(name='Test')
        assert schema.status == DocumentStatus.ACTIVE


class TestDocumentUpdate:
    """Tests for update schema."""

    def test_valid_update(self):
        schema = DocumentUpdate(name='Updated')
        assert schema.name == 'Updated'

    def test_empty_update(self):
        schema = DocumentUpdate()
        assert schema.name is None


class TestDocumentFilter:
    """Tests for filter schema."""

    def test_default_filter(self):
        schema = DocumentFilter()
        assert schema.search is None
        assert schema.status is None

    def test_with_search(self):
        schema = DocumentFilter(search='test')
        assert schema.search == 'test'
