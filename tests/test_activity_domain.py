"""Tests for activity domain."""

import pytest

from app.domains.activity_domain import (
    ActivityCreateDTO,
    ActivityRepository,
)


class TestActivityRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ActivityRepository()
        dto = ActivityCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ActivityRepository()
        dto = ActivityCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ActivityRepository()
        await repo.create(ActivityCreateDTO(name='A'))
        await repo.create(ActivityCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
