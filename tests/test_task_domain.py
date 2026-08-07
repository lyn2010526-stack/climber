"""Tests for task domain."""

import pytest

from app.domains.task_domain import (
    TaskCreateDTO,
    TaskRepository,
)


class TestTaskRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = TaskRepository()
        dto = TaskCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = TaskRepository()
        dto = TaskCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = TaskRepository()
        await repo.create(TaskCreateDTO(name='A'))
        await repo.create(TaskCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
