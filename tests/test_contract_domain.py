"""Tests for contract domain."""

import pytest

from app.domains.contract_domain import (
    ContractCreateDTO,
    ContractRepository,
)


class TestContractRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ContractRepository()
        dto = ContractCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ContractRepository()
        dto = ContractCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ContractRepository()
        await repo.create(ContractCreateDTO(name='A'))
        await repo.create(ContractCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
