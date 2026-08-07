"""Tests for channel domain."""

import pytest

from app.domains.channel_domain import (
    ChannelCreateDTO,
    ChannelRepository,
)


class TestChannelRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ChannelRepository()
        dto = ChannelCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ChannelRepository()
        dto = ChannelCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ChannelRepository()
        await repo.create(ChannelCreateDTO(name='A'))
        await repo.create(ChannelCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
