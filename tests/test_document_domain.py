"""Tests for document domain."""

import pytest

from app.domains.document_domain import (
    DocumentCreateDTO,
    DocumentRepository,
)


class TestDocumentRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = DocumentRepository()
        dto = DocumentCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = DocumentRepository()
        dto = DocumentCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = DocumentRepository()
        await repo.create(DocumentCreateDTO(name='A'))
        await repo.create(DocumentCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
