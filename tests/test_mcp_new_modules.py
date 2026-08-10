"""Tests for new MCP modules: models, oauth, registry, health, cache, router."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.mcp_cache import ToolResultCache
from app.tools.mcp_health import AutoRestart, MCPHealthMonitor, McpStatus
from app.tools.mcp_models import (
    MCPContent,
    MCPPrompt,
    MCPResource,
    MCPTool,
    MCPToolResult,
)
from app.tools.mcp_oauth import OAuthFlow, OAuthTokenStore
from app.tools.mcp_registry import MCPRegistryClient
from app.tools.mcp_router import MCPRouter

# -- Models Tests --


class TestMCPModels:
    def test_mcp_tool_creation(self) -> None:
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            inputSchema={"type": "object", "properties": {}},
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.title is None

    def test_mcp_tool_result_to_text(self) -> None:
        result = MCPToolResult(
            content=[
                MCPContent(type="text", text="Hello"),
                MCPContent(type="text", text="World"),
            ]
        )
        assert result.to_text() == "Hello\nWorld"
        assert result.isError is False

    def test_mcp_tool_result_error(self) -> None:
        result = MCPToolResult(
            content=[MCPContent(type="text", text="Error occurred")],
            isError=True,
        )
        assert result.isError is True
        assert result.to_text() == "Error occurred"

    def test_mcp_resource(self) -> None:
        resource = MCPResource(
            uri="file:///test.txt",
            name="test_file",
            description="A test file",
            mimeType="text/plain",
        )
        assert resource.uri == "file:///test.txt"
        assert resource.mimeType == "text/plain"

    def test_mcp_prompt(self) -> None:
        prompt = MCPPrompt(
            name="test_prompt",
            description="A test prompt",
            arguments=[{"name": "arg1", "description": "First arg"}],
        )
        assert prompt.name == "test_prompt"
        assert len(prompt.arguments) == 1


# -- Cache Tests --


class TestToolResultCache:
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self) -> None:
        cache = ToolResultCache()
        await cache.set("tool1", {"arg": "val"}, "result1")
        result = await cache.get("tool1", {"arg": "val"})
        assert result == "result1"

    @pytest.mark.asyncio
    async def test_cache_miss(self) -> None:
        cache = ToolResultCache()
        result = await cache.get("nonexistent", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry(self) -> None:
        cache = ToolResultCache()
        await cache.set("tool1", {"arg": "val"}, "result1", ttl_ms=1)
        await asyncio.sleep(0.01)
        result = await cache.get("tool1", {"arg": "val"})
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalidate(self) -> None:
        cache = ToolResultCache()
        await cache.set("tool1", {"arg": "val"}, "result1")
        await cache.set("tool1", {"arg": "val2"}, "result2")
        await cache.set("tool2", {"arg": "val"}, "result3")

        count = await cache.invalidate("tool1")
        assert count == 2
        assert await cache.get("tool2", {"arg": "val"}) == "result3"

    @pytest.mark.asyncio
    async def test_cache_stats(self) -> None:
        cache = ToolResultCache()
        await cache.set("tool1", {"arg": "val"}, "result1")
        await cache.get("tool1", {"arg": "val"})
        await cache.get("nonexistent", {})

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_cache_clear(self) -> None:
        cache = ToolResultCache()
        await cache.set("tool1", {"arg": "val"}, "result1")
        await cache.clear()
        assert await cache.get("tool1", {"arg": "val"}) is None


# -- OAuth Tests --


class TestOAuthTokenStore:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self) -> None:
        store = OAuthTokenStore()
        await store.set("https://server.com", {"access_token": "token123", "expires_in": 3600})
        result = await store.get("https://server.com")
        assert result is not None
        assert result["access_token"] == "token123"

    @pytest.mark.asyncio
    async def test_expired_token(self) -> None:
        store = OAuthTokenStore()
        await store.set("https://server.com", {"access_token": "token123", "expires_at": 0})
        result = await store.get("https://server.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_token(self) -> None:
        store = OAuthTokenStore()
        await store.set("https://server.com", {"access_token": "token123", "expires_in": 3600})
        await store.clear("https://server.com")
        result = await store.get("https://server.com")
        assert result is None


class TestOAuthFlow:
    def test_generate_pkce(self) -> None:
        flow = OAuthFlow()
        verifier, challenge = flow._generate_pkce()
        assert len(verifier) > 0
        assert len(challenge) == 64  # SHA256 hex digest

    @pytest.mark.asyncio
    async def test_get_authorization_url(self) -> None:
        flow = OAuthFlow()
        url = await flow.get_authorization_url(
            "https://server.com",
            "https://server.com/oauth/authorize",
            scopes=["read", "write"],
        )
        assert "response_type=code" in url
        assert "client_id=agent-engine" in url
        assert "scope=read+write" in url
        assert "code_challenge=" in url


# -- Registry Tests --


class TestMCPRegistryClient:
    @pytest.mark.asyncio
    async def test_search_returns_list_on_error(self) -> None:
        client = MCPRegistryClient(base_url="https://invalid-url-that-does-not-exist.ai")
        result = await client.search("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_server_returns_none_on_error(self) -> None:
        client = MCPRegistryClient(base_url="https://invalid-url-that-does-not-exist.ai")
        result = await client.get_server("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_popular_returns_list_on_error(self) -> None:
        client = MCPRegistryClient(base_url="https://invalid-url-that-does-not-exist.ai")
        result = await client.list_popular()
        assert result == []


# -- Health Monitor Tests --


class TestMCPHealthMonitor:
    @pytest.mark.asyncio
    async def test_check_disconnected_client(self) -> None:
        monitor = MCPHealthMonitor()
        mock_client = MagicMock()
        mock_client.name = "test_server"
        mock_client.session = None

        result = await monitor.check(mock_client)
        assert result.status == McpStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_check_connected_client(self) -> None:
        monitor = MCPHealthMonitor()
        mock_client = AsyncMock()
        mock_client.name = "test_server"
        mock_client.list_tools.return_value = []

        result = await monitor.check(mock_client)
        assert result.status == McpStatus.READY

    @pytest.mark.asyncio
    async def test_check_timeout(self) -> None:
        monitor = MCPHealthMonitor()
        mock_client = AsyncMock()
        mock_client.name = "test_server"
        mock_client.list_tools.side_effect = TimeoutError()

        result = await monitor.check(mock_client)
        assert result.status == McpStatus.ERROR
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_get_last_result(self) -> None:
        monitor = MCPHealthMonitor()
        mock_client = AsyncMock()
        mock_client.name = "test_server"
        mock_client.list_tools.return_value = []

        await monitor.check(mock_client)
        result = monitor.get_last_result("test_server")
        assert result is not None
        assert result.status == McpStatus.READY


class TestAutoRestart:
    @pytest.mark.asyncio
    async def test_handle_crash_success(self) -> None:
        restarter = AutoRestart(max_restarts=3, restart_delay=0.01)
        mock_client = AsyncMock()
        mock_client.name = "test_server"

        result = await restarter.handle_crash(mock_client)
        assert result is True
        mock_client.close.assert_called_once()
        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_crash_max_restarts(self) -> None:
        restarter = AutoRestart(max_restarts=1, restart_delay=0.01)
        mock_client = AsyncMock()
        mock_client.name = "test_server"
        mock_client.connect.side_effect = Exception("Connection failed")

        await restarter.handle_crash(mock_client)
        result = await restarter.handle_crash(mock_client)
        assert result is False

    def test_get_restart_count(self) -> None:
        restarter = AutoRestart()
        assert restarter.get_restart_count("test") == 0

    def test_reset(self) -> None:
        restarter = AutoRestart()
        restarter._restart_counts["test"] = 2
        restarter.reset("test")
        assert restarter.get_restart_count("test") == 0


# -- Router Tests --


class TestMCPRouter:
    def test_register_server(self) -> None:
        router = MCPRouter()
        mock_client = MagicMock()
        mock_client.tools = {"tool1": MCPTool(name="tool1", description="test", inputSchema={})}

        router.register_server("server1", mock_client)
        assert "server1" in router.servers

    def test_unregister_server(self) -> None:
        router = MCPRouter()
        mock_client = MagicMock()
        mock_client.tools = {}

        router.register_server("server1", mock_client)
        router.unregister_server("server1")
        assert "server1" not in router.servers

    def test_namespace_tool(self) -> None:
        result = MCPRouter.namespace_tool("my_server", "my_tool")
        assert result == "my_server__my_tool"

    def test_find_server_for_tool(self) -> None:
        router = MCPRouter()
        mock_client = MagicMock()
        mock_client.tools = {"tool1": MCPTool(name="tool1", description="test", inputSchema={})}

        router.register_server("server1", mock_client)
        assert router.find_server_for_tool("tool1") == "server1"
        assert router.find_server_for_tool("server1__tool1") == "server1"
        assert router.find_server_for_tool("nonexistent") is None

    @pytest.mark.asyncio
    async def test_route_tool_call(self) -> None:
        router = MCPRouter()
        mock_client = AsyncMock()
        mock_client.tools = {"tool1": MCPTool(name="tool1", description="test", inputSchema={})}
        mock_client.call_tool.return_value = MCPToolResult(
            content=[MCPContent(type="text", text="result")]
        )

        router.register_server("server1", mock_client)
        result = await router.route("tool1", {"arg": "val"})
        assert result.to_text() == "result"
        mock_client.call_tool.assert_called_once_with("tool1", {"arg": "val"})

    @pytest.mark.asyncio
    async def test_route_tool_not_found(self) -> None:
        router = MCPRouter()
        result = await router.route("nonexistent", {})
        assert result.isError is True
        assert "not found" in result.to_text()

    @pytest.mark.asyncio
    async def test_list_all_tools(self) -> None:
        router = MCPRouter()
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = [
            MCPTool(name="tool1", description="test", inputSchema={})
        ]

        router.register_server("server1", mock_client)
        tools = await router.list_all_tools()
        assert "server1" in tools
        assert len(tools["server1"]) == 1
