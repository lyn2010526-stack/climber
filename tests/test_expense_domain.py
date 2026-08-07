"""Tests for expense domain."""

import pytest

from app.domains.expense_domain import (
    ExpenseCreateDTO,
    ExpenseRepository,
)


class TestExpenseRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = ExpenseRepository()
        dto = ExpenseCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = ExpenseRepository()
        dto = ExpenseCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = ExpenseRepository()
        await repo.create(ExpenseCreateDTO(name='A'))
        await repo.create(ExpenseCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
