"""Tests for message domain."""

import pytest

from app.domains.message_domain import (
    MessageCreateDTO,
    MessageRepository,
)


class TestMessageRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = MessageRepository()
        dto = MessageCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = MessageRepository()
        dto = MessageCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = MessageRepository()
        await repo.create(MessageCreateDTO(name='A'))
        await repo.create(MessageCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
