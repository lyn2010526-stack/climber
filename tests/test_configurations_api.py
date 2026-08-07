"""Tests for configurations API."""

import pytest
from httpx import AsyncClient


class TestConfigurationAPI:
    """Tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_create(self, client: AsyncClient):
        response = await client.post('/configurations/', json={
            'name': 'test', 'description': 'test desc'
        })
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get(self, client: AsyncClient):
        response = await client.get('/configurations/1')
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_list(self, client: AsyncClient):
        response = await client.get('/configurations/')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update(self, client: AsyncClient):
        response = await client.put('/configurations/1', json={'name': 'updated'})
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_delete(self, client: AsyncClient):
        response = await client.delete('/configurations/1')
        assert response.status_code in (204, 404)
