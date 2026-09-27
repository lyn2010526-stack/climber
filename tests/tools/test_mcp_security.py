"""Security and lifecycle regressions for MCP integrations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.tools.mcp_client import MCPClient
from app.tools.mcp_oauth import OAuthFlow
from app.tools.mcp_registry import MCPRegistryClient
from app.tools.mcp_router import MCPRouter


@pytest.mark.asyncio
async def test_client_closes_transport_when_initialization_fails(monkeypatch):
    client = MCPClient("broken", transport="streamable_http", url="https://example.com/mcp")
    transport = AsyncMock()
    transport.__aenter__.return_value = (object(), object(), object())

    async def fail_initialize():
        raise RuntimeError("authorization: Bearer secret-token")

    monkeypatch.setattr("app.tools.mcp_client._MCP_AVAILABLE", True)
    monkeypatch.setattr("app.tools.mcp_client.ClientSession", lambda *_: AsyncMock())
    monkeypatch.setattr("app.tools.mcp_client.streamablehttp_client", lambda **_: transport)
    monkeypatch.setattr(client, "_initialize", fail_initialize)

    with pytest.raises(RuntimeError):
        await client.connect()

    transport.__aexit__.assert_awaited_once()
    assert client.session is None
    assert client._connect_cm is None


@pytest.mark.asyncio
async def test_client_closes_transport_when_session_enter_fails(monkeypatch):
    client = MCPClient("broken", transport="streamable_http", url="https://example.com/mcp")
    transport = AsyncMock()
    transport.__aenter__.return_value = (object(), object(), object())
    session = AsyncMock()
    session.__aenter__.side_effect = RuntimeError("session secret")

    monkeypatch.setattr("app.tools.mcp_client._MCP_AVAILABLE", True)
    monkeypatch.setattr("app.tools.mcp_client.ClientSession", lambda *_: session)
    monkeypatch.setattr("app.tools.mcp_client.streamablehttp_client", lambda **_: transport)

    with pytest.raises(RuntimeError):
        await client.connect()

    session.__aexit__.assert_not_awaited()
    transport.__aexit__.assert_awaited_once()
    assert client.session is None
    assert client._connect_cm is None


@pytest.mark.asyncio
async def test_client_close_is_idempotent_after_partial_connect(monkeypatch):
    client = MCPClient("broken", transport="streamable_http", url="https://example.com/mcp")
    transport = AsyncMock()
    transport.__aenter__.side_effect = RuntimeError("connect secret")

    monkeypatch.setattr("app.tools.mcp_client._MCP_AVAILABLE", True)
    monkeypatch.setattr("app.tools.mcp_client.streamablehttp_client", lambda **_: transport)

    with pytest.raises(RuntimeError):
        await client.connect()
    await client.close()

    transport.__aexit__.assert_not_awaited()
    assert client.is_connected is False


@pytest.mark.asyncio
async def test_client_tool_error_does_not_return_exception_text():
    client = MCPClient("server")
    client.session = SimpleNamespace(call_tool=AsyncMock(side_effect=RuntimeError("token=secret")))

    result = await client.call_tool("private", {})

    assert result.isError is True
    assert result.content[0].text == "MCP tool call failed"
    assert "secret" not in result.to_text()


@pytest.mark.asyncio
async def test_router_error_does_not_return_exception_text():
    router = MCPRouter()
    client = SimpleNamespace(
        tools={"private": object()},
        call_tool=AsyncMock(side_effect=RuntimeError("Authorization: Bearer secret")),
    )
    router.register_server("server", client)

    result = await router.route("private", {})

    assert result.isError is True
    assert result.content[0].text == "MCP tool routing failed"


def test_registry_rejects_unsafe_base_url():
    with pytest.raises(ValueError, match=r"HTTP\(S\)"):
        MCPRegistryClient("file:///tmp/registry")

    with pytest.raises(ValueError, match="SSRF"):
        MCPRegistryClient("http://127.0.0.1:8080/api")

    with pytest.raises(ValueError, match="credentials"):
        MCPRegistryClient("https://user:password@example.com/api")


@pytest.mark.asyncio
async def test_oauth_rejects_unsafe_endpoints():
    flow = OAuthFlow()

    with pytest.raises(ValueError, match="SSRF"):
        await flow.get_authorization_url(
            "https://oauth.example.com",
            "http://127.0.0.1:8080/authorize",
        )

    with pytest.raises(ValueError, match="credentials"):
        await flow.get_authorization_url(
            "https://user:password@example.com",
            "https://oauth.example.com/authorize",
        )
