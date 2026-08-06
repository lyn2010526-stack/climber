from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.tools.mcp_client import MCPClient

SERVER_PATH = Path(__file__).parent / "fixtures" / "mcp_stdio_server.py"


@pytest.mark.asyncio
async def test_stdio_client_discovers_calls_and_closes_server() -> None:
    client = MCPClient(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        name="fixture",
    )

    try:
        await client.start()

        definitions = client.get_tool_definitions()
        assert definitions == [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "Add two integers.",
                    "parameters": {
                        "properties": {
                            "a": {"title": "A", "type": "integer"},
                            "b": {"title": "B", "type": "integer"},
                        },
                        "required": ["a", "b"],
                        "title": "addArguments",
                        "type": "object",
                    },
                },
            }
        ]
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.to_text() == "5"
        assert result.isError is False
        assert client.is_connected is True
    finally:
        await client.stop()

    assert client.is_connected is False
