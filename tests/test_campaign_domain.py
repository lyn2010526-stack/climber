"""Tests for campaign domain."""

import pytest

from app.domains.campaign_domain import (
    CampaignCreateDTO,
    CampaignRepository,
)


class TestCampaignRepository:
    """Tests for repository."""

    @pytest.mark.asyncio
    async def test_create(self):
        repo = CampaignRepository()
        dto = CampaignCreateDTO(name='Test')
        entity = await repo.create(dto)
        assert entity.name == 'Test'
        assert entity.id

    @pytest.mark.asyncio
    async def test_get(self):
        repo = CampaignRepository()
        dto = CampaignCreateDTO(name='Test')
        entity = await repo.create(dto)
        found = await repo.get(entity.id)
        assert found is not None
        assert found.name == 'Test'

    @pytest.mark.asyncio
    async def test_list_all(self):
        repo = CampaignRepository()
        await repo.create(CampaignCreateDTO(name='A'))
        await repo.create(CampaignCreateDTO(name='B'))
        entities = await repo.list_all()
        assert len(entities) == 2
