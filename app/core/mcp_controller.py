"""MCP (Model Context Protocol) controller."""
from __future__ import annotations

from enum import StrEnum
from typing import Any


class McpStatus(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


class McpController:
    """Controls MCP server lifecycle."""

    def __init__(self) -> None:
        self._status = McpStatus.STOPPED
        self._servers: dict[str, Any] = {}

    def get_status(self) -> McpStatus:
        return self._status

    async def start(self) -> bool:
        self._status = McpStatus.RUNNING
        return True

    async def stop(self) -> bool:
        self._status = McpStatus.STOPPED
        return True

    def register_server(self, name: str, config: dict[str, Any]) -> None:
        self._servers[name] = config
