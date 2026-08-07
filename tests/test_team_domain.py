"""Tests for team domain."""

import pytest

from app.domains.team_domain import (
    TeamCreateDTO,
    TeamRepository,
)


class TestTeamRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = TeamRepository()
        dto = TeamCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = TeamRepository()
        dto = TeamCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = TeamRepository()
        await repo.create(TeamCreateDTO(name='A'))
        await repo.create(TeamCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
