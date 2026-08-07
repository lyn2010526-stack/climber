"""Tests for budget domain."""

import pytest

from app.domains.budget_domain import (
    BudgetCreateDTO,
    BudgetRepository,
)


class TestBudgetRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = BudgetRepository()
        dto = BudgetCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = BudgetRepository()
        dto = BudgetCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = BudgetRepository()
        await repo.create(BudgetCreateDTO(name='A'))
        await repo.create(BudgetCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
