"""Tests for roadmap domain."""

import pytest

from app.domains.roadmap_domain import (
    RoadmapCreateDTO,
    RoadmapRepository,
)


class TestRoadmapRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = RoadmapRepository()
        dto = RoadmapCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = RoadmapRepository()
        dto = RoadmapCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = RoadmapRepository()
        await repo.create(RoadmapCreateDTO(name='A'))
        await repo.create(RoadmapCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
