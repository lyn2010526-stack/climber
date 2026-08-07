"""Tests for workspace domain."""

import pytest

from app.domains.workspace_domain import (
    WorkspaceCreateDTO,
    WorkspaceRepository,
)


class TestWorkspaceRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = WorkspaceRepository()
        dto = WorkspaceCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = WorkspaceRepository()
        dto = WorkspaceCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = WorkspaceRepository()
        await repo.create(WorkspaceCreateDTO(name='A'))
        await repo.create(WorkspaceCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
