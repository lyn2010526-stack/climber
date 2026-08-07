"""Tests for file domain."""

import pytest

from app.domains.file_domain import (
    FileCreateDTO,
    FileRepository,
)


class TestFileRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = FileRepository()
        dto = FileCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = FileRepository()
        dto = FileCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = FileRepository()
        await repo.create(FileCreateDTO(name='A'))
        await repo.create(FileCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
