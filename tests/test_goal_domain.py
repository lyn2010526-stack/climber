"""Tests for goal domain."""

import pytest

from app.domains.goal_domain import (
    GoalCreateDTO,
    GoalRepository,
)


class TestGoalRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = GoalRepository()
        dto = GoalCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = GoalRepository()
        dto = GoalCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = GoalRepository()
        await repo.create(GoalCreateDTO(name='A'))
        await repo.create(GoalCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
