"""Tests for meeting domain."""

import pytest

from app.domains.meeting_domain import (
    MeetingCreateDTO,
    MeetingRepository,
)


class TestMeetingRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = MeetingRepository()
        dto = MeetingCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = MeetingRepository()
        dto = MeetingCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = MeetingRepository()
        await repo.create(MeetingCreateDTO(name='A'))
        await repo.create(MeetingCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
