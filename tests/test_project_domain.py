"""Tests for project domain."""

import pytest

from app.domains.project_domain import (
    ProjectCreateDTO,
    ProjectRepository,
)


class TestProjectRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ProjectRepository()
        dto = ProjectCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ProjectRepository()
        dto = ProjectCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ProjectRepository()
        await repo.create(ProjectCreateDTO(name='A'))
        await repo.create(ProjectCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
