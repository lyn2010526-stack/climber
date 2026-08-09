"""MCP process controller with health monitoring and auto-restart."""

from __future__ import annotations

import asyncio
import subprocess
import time
from enum import Enum
from typing import Optional


class McpStatus(str, Enum):
    """MCP process status."""

    DISCONNECTED = "disconnected"
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"
    RESTARTING = "restarting"


class McpStartResult:
    """Result of MCP start operation."""

    def __init__(
        self,
        success: bool,
        status: McpStatus,
        error: str = "",
        fallback: str = "",
    ) -> None:
        self.success = success
        self.status = status
        self.error = error
        self.fallback = fallback


class McpController:
    """Manages jCodeMunch MCP process lifecycle."""

    def __init__(
        self,
        command: str = "npx",
        args: list[str] | None = None,
        startup_timeout: int = 10,
        max_restarts: int = 3,
    ) -> None:
        self.command = command
        self.args = args or ["-y", "jcodemunch-mcp"]
        self.startup_timeout = startup_timeout
        self.max_restarts = max_restarts
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self._status = McpStatus.DISCONNECTED
        self._last_error: str = ""

    @property
    def status(self) -> McpStatus:
        """Get current MCP status."""
        return self._status

    @property
    def last_error(self) -> str:
        """Get last error message."""
        return self._last_error

    async def start(self) -> McpStartResult:
        """Start MCP process with timeout."""
        if self._status == McpStatus.READY:
            return McpStartResult(success=True, status=McpStatus.READY)

        self._status = McpStatus.STARTING
        self._last_error = ""

        try:
            await asyncio.wait_for(self._start_process(), timeout=self.startup_timeout)
            self._status = McpStatus.READY
            self.restart_count = 0
            return McpStartResult(success=True, status=McpStatus.READY)
        except asyncio.TimeoutError:
            self._status = McpStatus.ERROR
            self._last_error = f"MCP 启动超时（{self.startup_timeout}秒）"
            return McpStartResult(
                success=False,
                status=McpStatus.ERROR,
                error=self._last_error,
                fallback="已降级为基础模式，对话功能正常",
            )
        except Exception as e:
            self._status = McpStatus.ERROR
            self._last_error = f"MCP 启动失败: {str(e)}"
            return McpStartResult(
                success=False,
                status=McpStatus.ERROR,
                error=self._last_error,
                fallback="已降级为基础模式，对话功能正常",
            )

    async def _start_process(self) -> None:
        """Internal process startup."""
        self.process = subprocess.Popen(
            [self.command] + self.args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait briefly for process to initialize
        await asyncio.sleep(0.5)
        if self.process.poll() is not None:
            raise RuntimeError("MCP process exited immediately")

    async def stop(self) -> None:
        """Stop MCP process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self._status = McpStatus.DISCONNECTED

    async def restart(self) -> McpStartResult:
        """Restart MCP process (with restart count limit)."""
        if self.restart_count >= self.max_restarts:
            self._status = McpStatus.ERROR
            self._last_error = f"MCP 重启次数已达上限（{self.max_restarts}次）"
            return McpStartResult(
                success=False,
                status=McpStatus.ERROR,
                error=self._last_error,
                fallback="已永久禁用MCP，对话功能正常",
            )

        self._status = McpStatus.RESTARTING
        self.restart_count += 1

        await self.stop()
        result = await self.start()

        if result.success:
            self.restart_count = 0

        return result

    async def health_check(self) -> McpStatus:
        """Check MCP process health."""
        if self.process is None:
            self._status = McpStatus.DISCONNECTED
            return McpStatus.DISCONNECTED

        return_code = self.process.poll()
        if return_code is not None:
            self._status = McpStatus.ERROR
            self._last_error = f"MCP 进程已退出，代码: {return_code}"
            return McpStatus.ERROR

        self._status = McpStatus.READY
        return McpStatus.READY

    def get_status(self) -> McpStatus:
        """Get current status synchronously."""
        return self._status
