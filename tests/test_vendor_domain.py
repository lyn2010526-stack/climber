"""Tests for vendor domain."""

import pytest

from app.domains.vendor_domain import (
    VendorCreateDTO,
    VendorRepository,
)


class TestVendorRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = VendorRepository()
        dto = VendorCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = VendorRepository()
        dto = VendorCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = VendorRepository()
        await repo.create(VendorCreateDTO(name='A'))
        await repo.create(VendorCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
