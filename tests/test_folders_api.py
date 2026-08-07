"""Tests for folders API."""

import pytest
from httpx import AsyncClient


class TestFolderAPI:
    """Tests for API endpoints."""

    @pytest.mark.asyncio
    async def test_create(self, client: AsyncClient):
        response = await client.post('/folders/', json={
            'name': 'test', 'description': 'test desc'
        })
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get(self, client: AsyncClient):
        response = await client.get('/folders/1')
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_list(self, client: AsyncClient):
        response = await client.get('/folders/')
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update(self, client: AsyncClient):
        response = await client.put('/folders/1', json={'name': 'updated'})
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_delete(self, client: AsyncClient):
        response = await client.delete('/folders/1')
        assert response.status_code in (204, 404)
