"""Tests for MCP Registry client."""

from __future__ import annotations

import unittest.mock as mock

import httpx
import pytest

from app.tools.mcp_registry import DEFAULT_REGISTRY_URL, MCPRegistryClient


class TestMCPRegistryClientInit:
    """Tests for MCPRegistryClient initialization."""

    def test_default_url(self):
        client = MCPRegistryClient()
        assert client.base_url == DEFAULT_REGISTRY_URL

    def test_custom_url(self):
        client = MCPRegistryClient(base_url="https://custom.registry.com/api")
        assert client.base_url == "https://custom.registry.com/api"

    def test_url_trailing_slash_stripped(self):
        client = MCPRegistryClient(base_url="https://example.com/api/")
        assert client.base_url == "https://example.com/api"


class TestSearch:
    """Tests for search method."""

    @pytest.mark.asyncio
    async def test_search_returns_list(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = [{"name": "server1"}, {"name": "server2"}]
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.search("test query")

        assert len(result) == 2
        assert result[0]["name"] == "server1"

    @pytest.mark.asyncio
    async def test_search_dict_with_servers_key(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"servers": [{"name": "s1"}]}
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.search("test")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_empty_response(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.search("test")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(side_effect=httpx.HTTPError("fail"))
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.search("test")

        assert result == []


class TestGetServer:
    """Tests for get_server method."""

    @pytest.mark.asyncio
    async def test_get_server_success(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"name": "test-server", "tools": []}
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.get_server("test-server")

        assert result == {"name": "test-server", "tools": []}

    @pytest.mark.asyncio
    async def test_get_server_not_found(self):
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_error = httpx.HTTPStatusError("404", request=mock.MagicMock(), response=mock_response)

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(side_effect=mock_error)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.get_server("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_server_http_error(self):
        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(side_effect=httpx.HTTPError("fail"))
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.get_server("test")

        assert result is None


class TestListPopular:
    """Tests for list_popular method."""

    @pytest.mark.asyncio
    async def test_list_popular_returns_list(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = [{"name": "popular1"}]
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.list_popular(limit=5)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_popular_http_error(self):
        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(side_effect=httpx.HTTPError("fail"))
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.list_popular()

        assert result == []


class TestListCategories:
    """Tests for list_categories method."""

    @pytest.mark.asyncio
    async def test_list_categories_returns_list(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = ["search", "data", "tools"]
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.list_categories()

        assert len(result) == 3
        assert "search" in result

    @pytest.mark.asyncio
    async def test_list_categories_dict_response(self):
        mock_response = mock.MagicMock()
        mock_response.json.return_value = {"categories": ["cat1", "cat2"]}
        mock_response.raise_for_status = mock.MagicMock()

        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.list_categories()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_categories_http_error(self):
        mock_client = mock.MagicMock()
        mock_client.get = mock.AsyncMock(side_effect=httpx.HTTPError("fail"))
        mock_client.__aenter__ = mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mock.AsyncMock(return_value=None)

        with mock.patch("httpx.AsyncClient", return_value=mock_client):
            client = MCPRegistryClient()
            result = await client.list_categories()

        assert result == []
