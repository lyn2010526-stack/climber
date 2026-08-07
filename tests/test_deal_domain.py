"""Tests for deal domain."""

import pytest

from app.domains.deal_domain import (
    DealCreateDTO,
    DealRepository,
)


class TestDealRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = DealRepository()
        dto = DealCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = DealRepository()
        dto = DealCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = DealRepository()
        await repo.create(DealCreateDTO(name='A'))
        await repo.create(DealCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
