# tests/test_mcp_bridge.py
from unittest.mock import AsyncMock, patch

import pytest

from app.core.tool_runtime import ToolRuntime
from app.engine.mcp_bridge import MCPBridge


@pytest.fixture
def runtime():
    return ToolRuntime()


@pytest.fixture
def bridge(runtime):
    return MCPBridge(runtime)


def test_bridge_initialization(bridge):
    assert bridge.runtime is not None
    assert bridge._servers == {}


@pytest.mark.asyncio
async def test_connect_and_register_tools(bridge):
    mock_client = AsyncMock()
    mock_client.list_tools = AsyncMock(return_value=[
        {"name": "search", "description": "Search the web", "inputSchema": {"type": "object"}},
    ])
    mock_client.call_tool = AsyncMock(return_value={"result": "found"})

    with patch("app.tools.mcp_client.MCPClient", return_value=mock_client):
        await bridge.connect_server("http://localhost:3001", "test-server")

    tools = bridge.runtime.list_tools()
    tool_names = [t.name for t in tools]
    assert any("search" in name for name in tool_names)


def test_get_tool_descriptions_for_prompt(bridge):
    bridge._servers["test"] = [{"name": "fetch", "description": "Fetch URLs"}]
    bridge._tool_docs["test.fetch"] = "- test.fetch: Fetch URLs"
    desc = bridge.get_tool_descriptions_for_prompt()
    assert "fetch" in desc
    assert "Fetch URLs" in desc
