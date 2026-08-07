"""Tests for milestone domain."""

import pytest

from app.domains.milestone_domain import (
    MilestoneCreateDTO,
    MilestoneRepository,
)


class TestMilestoneRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = MilestoneRepository()
        dto = MilestoneCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = MilestoneRepository()
        dto = MilestoneCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = MilestoneRepository()
        await repo.create(MilestoneCreateDTO(name='A'))
        await repo.create(MilestoneCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
