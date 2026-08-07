"""Tests for event domain."""

import pytest

from app.domains.event_domain import (
    EventCreateDTO,
    EventRepository,
)


class TestEventRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = EventRepository()
        dto = EventCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = EventRepository()
        dto = EventCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = EventRepository()
        await repo.create(EventCreateDTO(name='A'))
        await repo.create(EventCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
