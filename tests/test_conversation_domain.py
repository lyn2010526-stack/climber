"""Tests for conversation domain."""

import pytest

from app.domains.conversation_domain import (
    ConversationCreateDTO,
    ConversationRepository,
)


class TestConversationRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ConversationRepository()
        dto = ConversationCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ConversationRepository()
        dto = ConversationCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ConversationRepository()
        await repo.create(ConversationCreateDTO(name='A'))
        await repo.create(ConversationCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
