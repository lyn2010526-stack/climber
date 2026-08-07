"""Tests for notification domain."""

import pytest

from app.domains.notification_domain import (
    NotificationCreateDTO,
    NotificationRepository,
)


class TestNotificationRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = NotificationRepository()
        dto = NotificationCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = NotificationRepository()
        dto = NotificationCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = NotificationRepository()
        await repo.create(NotificationCreateDTO(name='A'))
        await repo.create(NotificationCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
