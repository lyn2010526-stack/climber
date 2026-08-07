"""Tests for lead domain."""

import pytest

from app.domains.lead_domain import (
    LeadCreateDTO,
    LeadRepository,
)


class TestLeadRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = LeadRepository()
        dto = LeadCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = LeadRepository()
        dto = LeadCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = LeadRepository()
        await repo.create(LeadCreateDTO(name='A'))
        await repo.create(LeadCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
