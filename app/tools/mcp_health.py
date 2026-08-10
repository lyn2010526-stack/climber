"""MCP server health monitoring and auto-restart."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()


class McpStatus(StrEnum):
    """MCP process status."""

    DISCONNECTED = "disconnected"
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"
    RESTARTING = "restarting"


class HealthCheckResult:
    """Result of a health check."""

    def __init__(
        self,
        status: McpStatus,
        latency_ms: float = 0.0,
        error: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.latency_ms = latency_ms
        self.error = error
        self.details = details or {}


class MCPHealthMonitor:
    """Monitor MCP server health with periodic checks."""

    def __init__(self, check_interval: int = 30) -> None:
        self.check_interval = check_interval
        self._monitors: dict[str, asyncio.Task] = {}
        self._results: dict[str, HealthCheckResult] = {}

    async def check(self, client: Any) -> HealthCheckResult:
        """Perform a single health check on an MCP server."""
        import time

        start = time.monotonic()
        try:
            if hasattr(client, "session") and client.session is None:
                result = HealthCheckResult(
                    status=McpStatus.DISCONNECTED,
                    error="Not connected",
                )
            elif hasattr(client, "list_tools"):
                tools = await asyncio.wait_for(
                    client.list_tools(),
                    timeout=settings.mcp_timeout,
                )
                latency = (time.monotonic() - start) * 1000
                result = HealthCheckResult(
                    status=McpStatus.READY,
                    latency_ms=latency,
                    details={"tools_count": len(tools)},
                )
            else:
                result = HealthCheckResult(
                    status=McpStatus.READY,
                    latency_ms=(time.monotonic() - start) * 1000,
                )
        except TimeoutError:
            result = HealthCheckResult(
                status=McpStatus.ERROR,
                error="Health check timed out",
            )
        except Exception as e:
            result = HealthCheckResult(
                status=McpStatus.ERROR,
                error=str(e),
            )

        name = getattr(client, "name", "unknown")
        self._results[name] = result
        return result

    async def start_monitoring(self, client: Any, interval: int | None = None) -> None:
        """Start periodic health monitoring for a client."""
        name = getattr(client, "name", "unknown")
        if name in self._monitors:
            return

        interval = interval or self.check_interval

        async def _monitor_loop() -> None:
            while True:
                try:
                    result = await self.check(client)
                    if result.status == McpStatus.ERROR:
                        logger.warning(
                            "Health check failed",
                            server=name,
                            error=result.error,
                        )
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Monitor loop error", server=name, error=str(e))
                await asyncio.sleep(interval)

        self._monitors[name] = asyncio.create_task(_monitor_loop())
        logger.info("Health monitoring started", server=name, interval=interval)

    async def stop_monitoring(self, client: Any) -> None:
        """Stop monitoring a specific client."""
        name = getattr(client, "name", "unknown")
        task = self._monitors.pop(name, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info("Health monitoring stopped", server=name)

    async def stop_all(self) -> None:
        """Stop all monitoring tasks."""
        for _, task in list(self._monitors.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._monitors.clear()

    def get_last_result(self, name: str) -> HealthCheckResult | None:
        """Get the most recent health check result."""
        return self._results.get(name)


class AutoRestart:
    """Auto-restart failed MCP servers with exponential backoff."""

    def __init__(self, max_restarts: int = 3, restart_delay: float = 5.0) -> None:
        self.max_restarts = max_restarts
        self.restart_delay = restart_delay
        self._restart_counts: dict[str, int] = {}
        self._last_restart: dict[str, float] = {}

    async def handle_crash(self, client: Any) -> bool:
        """Attempt to restart a crashed MCP server."""
        import time

        name = getattr(client, "name", "unknown")
        count = self._restart_counts.get(name, 0)

        if count >= self.max_restarts:
            logger.error(
                "Max restarts reached",
                server=name,
                max_restarts=self.max_restarts,
            )
            return False

        delay = self.restart_delay * (2 ** count)
        logger.info(
            "Restarting MCP server",
            server=name,
            attempt=count + 1,
            delay=delay,
        )
        await asyncio.sleep(delay)

        try:
            if hasattr(client, "close"):
                await client.close()
            if hasattr(client, "connect"):
                await client.connect()
            self._restart_counts[name] = 0
            self._last_restart[name] = time.time()
            logger.info("MCP server restarted successfully", server=name)
            return True
        except Exception as e:
            self._restart_counts[name] = count + 1
            logger.error("Restart failed", server=name, error=str(e))
            return False

    def get_restart_count(self, name: str) -> int:
        """Get current restart count for a server."""
        return self._restart_counts.get(name, 0)

    def reset(self, name: str) -> None:
        """Reset restart count for a server."""
        self._restart_counts.pop(name, None)
