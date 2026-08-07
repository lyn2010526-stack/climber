"""Tests for folder domain."""

import pytest

from app.domains.folder_domain import (
    FolderCreateDTO,
    FolderRepository,
)


class TestFolderRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = FolderRepository()
        dto = FolderCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = FolderRepository()
        dto = FolderCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = FolderRepository()
        await repo.create(FolderCreateDTO(name='A'))
        await repo.create(FolderCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
