"""Tests for organization domain."""

import pytest

from app.domains.organization_domain import (
    OrganizationCreateDTO,
    OrganizationRepository,
)


class TestOrganizationRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = OrganizationRepository()
        dto = OrganizationCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = OrganizationRepository()
        dto = OrganizationCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = OrganizationRepository()
        await repo.create(OrganizationCreateDTO(name='A'))
        await repo.create(OrganizationCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
