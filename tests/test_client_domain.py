"""Tests for client domain."""

import pytest

from app.domains.client_domain import (
    ClientCreateDTO,
    ClientRepository,
)


class TestClientRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ClientRepository()
        dto = ClientCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ClientRepository()
        dto = ClientCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ClientRepository()
        await repo.create(ClientCreateDTO(name='A'))
        await repo.create(ClientCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
