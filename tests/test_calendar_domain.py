"""Tests for calendar domain."""

import pytest

from app.domains.calendar_domain import (
    CalendarCreateDTO,
    CalendarRepository,
)


class TestCalendarRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = CalendarRepository()
        dto = CalendarCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = CalendarRepository()
        dto = CalendarCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = CalendarRepository()
        await repo.create(CalendarCreateDTO(name='A'))
        await repo.create(CalendarCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
