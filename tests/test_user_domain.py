"""Tests for user domain."""

import pytest

from app.domains.user_domain import (
    UserCreateDTO,
    UserRepository,
)


class TestUserRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = UserRepository()
        dto = UserCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = UserRepository()
        dto = UserCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = UserRepository()
        await repo.create(UserCreateDTO(name='A'))
        await repo.create(UserCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
