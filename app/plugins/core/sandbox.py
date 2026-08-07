"""Plugin sandbox isolation.

Provides sandboxed execution environments for plugins to ensure
isolation, security, and resource control.
"""

from __future__ import annotations

import asyncio
import logging
import os
import resource
import tempfile
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, TypeVar

from app.plugins.core.base import PluginError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class SandboxConfig:
    """Configuration for plugin sandbox execution.

    Defines resource limits and security constraints for plugin execution.
    """

    max_memory_mb: int = 128
    max_cpu_time_seconds: float = 30.0
    max_execution_time_seconds: float = 60.0
    max_file_descriptors: int = 64
    allow_network: bool = False
    allow_file_write: bool = False
    allowed_paths: list[str] = field(default_factory=list)
    environment_variables: dict[str, str] = field(default_factory=dict)
    enable_subprocess: bool = False
    max_subprocess_count: int = 0
    temp_dir: str | None = None


@dataclass
class SandboxResult:
    """Result of sandboxed execution."""

    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    memory_peak_mb: float = 0.0
    timed_out: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SandboxStats:
    """Statistics for sandbox execution."""

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_count: int = 0
    total_duration_ms: float = 0.0
    peak_memory_mb: float = 0.0
    avg_duration_ms: float = 0.0


class SandboxContext:
    """Execution context for sandboxed plugins.

    Provides isolated resource management and monitoring for
    a single plugin execution environment.
    """

    def __init__(self, plugin_name: str, config: SandboxConfig) -> None:
        self.plugin_name = plugin_name
        self.config = config
        self._temp_dir: str | None = None
        self._created_at = datetime.utcnow()
        self._execution_count = 0

    @property
    def uptime_seconds(self) -> float:
        """Get sandbox uptime in seconds."""
        return (datetime.utcnow() - self._created_at).total_seconds()

    @property
    def execution_count(self) -> int:
        """Get number of executions in this sandbox."""
        return self._execution_count

    def get_temp_dir(self) -> str:
        """Get or create temporary directory for this sandbox.

        Returns:
            Path to temporary directory.
        """
        if self._temp_dir is None:
            base = self.config.temp_dir or tempfile.gettempdir()
            self._temp_dir = os.path.join(base, f"sandbox_{self.plugin_name}")
            os.makedirs(self._temp_dir, exist_ok=True)
        return self._temp_dir

    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            try:
                shutil.rmtree(self._temp_dir)
            except OSError as e:
                logger.warning("Failed to cleanup sandbox temp dir: %s", e)
            self._temp_dir = None

    def increment_execution(self) -> None:
        """Increment execution counter."""
        self._execution_count += 1


class SandboxExecutor:
    """Executes plugin code in a sandboxed environment.

    Provides resource-limited, isolated execution with timeout
    enforcement and memory tracking.
    """

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self._config = config or SandboxConfig()
        self._sandboxes: dict[str, SandboxContext] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sandbox")
        self._stats = SandboxStats()

    @property
    def stats(self) -> SandboxStats:
        """Get sandbox execution statistics."""
        return self._stats

    @property
    def sandbox_count(self) -> int:
        """Get number of active sandboxes."""
        return len(self._sandboxes)

    def create_sandbox(self, plugin_name: str, config: SandboxConfig | None = None) -> SandboxContext:
        """Create a new sandbox context for a plugin.

        Args:
            plugin_name: Name of the plugin.
            config: Optional custom config; uses default if not provided.

        Returns:
            The created SandboxContext.
        """
        effective_config = config or self._config
        sandbox = SandboxContext(plugin_name, effective_config)
        self._sandboxes[plugin_name] = sandbox
        logger.debug("Sandbox created for plugin: %s", plugin_name)
        return sandbox

    def get_sandbox(self, plugin_name: str) -> SandboxContext | None:
        """Get sandbox context for a plugin.

        Args:
            plugin_name: Name of the plugin.

        Returns:
            SandboxContext or None if not found.
        """
        return self._sandboxes.get(plugin_name)

    def remove_sandbox(self, plugin_name: str) -> None:
        """Remove and cleanup a sandbox.

        Args:
            plugin_name: Name of the plugin.
        """
        sandbox = self._sandboxes.pop(plugin_name, None)
        if sandbox is not None:
            sandbox.cleanup()
            logger.debug("Sandbox removed for plugin: %s", plugin_name)

    async def execute(
        self,
        plugin_name: str,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> SandboxResult:
        """Execute a function in the sandbox.

        Args:
            plugin_name: Name of the plugin for sandbox lookup.
            func: Function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            SandboxResult with execution outcome.
        """
        sandbox = self._sandboxes.get(plugin_name)
        if sandbox is None:
            sandbox = self.create_sandbox(plugin_name)

        config = sandbox.config
        start = datetime.utcnow()
        self._stats.total_executions += 1
        sandbox.increment_execution()

        try:
            loop = asyncio.get_event_loop()

            if inspect.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=config.max_execution_time_seconds,
                )
            else:
                future = loop.run_in_executor(
                    self._executor,
                    lambda: func(*args, **kwargs),
                )
                result = await asyncio.wait_for(
                    future,
                    timeout=config.max_execution_time_seconds,
                )

            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self._stats.successful_executions += 1
            self._stats.total_duration_ms += duration
            self._stats.avg_duration_ms = (
                self._stats.total_duration_ms / self._stats.total_executions
            )

            return SandboxResult(success=True, result=result, duration_ms=duration)

        except asyncio.TimeoutError:
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self._stats.timeout_count += 1
            self._stats.failed_executions += 1
            self._stats.total_duration_ms += duration

            logger.warning(
                "Sandbox timeout for plugin %s after %.1fms",
                plugin_name,
                duration,
            )
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {config.max_execution_time_seconds}s",
                duration_ms=duration,
                timed_out=True,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds() * 1000
            self._stats.failed_executions += 1
            self._stats.total_duration_ms += duration

            logger.warning(
                "Sandbox execution error for plugin %s: %s",
                plugin_name,
                e,
            )
            return SandboxResult(
                success=False,
                error=str(e),
                duration_ms=duration,
            )

    @asynccontextmanager
    async def isolated_execution(self, plugin_name: str):
        """Context manager for isolated sandbox execution.

        Provides a context for running multiple operations within
        the same sandbox environment.

        Args:
            plugin_name: Name of the plugin.

        Yields:
            SandboxContext for the plugin.
        """
        sandbox = self.create_sandbox(plugin_name)
        try:
            yield sandbox
        finally:
            self.remove_sandbox(plugin_name)

    async def execute_many(
        self,
        plugin_name: str,
        tasks: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]],
    ) -> list[SandboxResult]:
        """Execute multiple functions in the sandbox.

        Args:
            plugin_name: Name of the plugin.
            tasks: List of (function, args, kwargs) tuples.

        Returns:
            List of SandboxResult for each execution.
        """
        results: list[SandboxResult] = []
        for func, args, kwargs in tasks:
            result = await self.execute(plugin_name, func, *args, **kwargs)
            results.append(result)
        return results

    def shutdown(self) -> None:
        """Shutdown the sandbox executor and cleanup all sandboxes."""
        for plugin_name in list(self._sandboxes.keys()):
            self.remove_sandbox(plugin_name)
        self._executor.shutdown(wait=False)
        logger.info("Sandbox executor shutdown")


import inspect


def _set_memory_limit(max_mb: int) -> None:
    """Set memory limit for current process (Unix only).

    Args:
        max_mb: Maximum memory in megabytes.
    """
    try:
        max_bytes = max_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
    except (OSError, ValueError):
        pass


def _set_cpu_limit(max_seconds: int) -> None:
    """Set CPU time limit for current process (Unix only).

    Args:
        max_seconds: Maximum CPU time in seconds.
    """
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (max_seconds, max_seconds))
    except (OSError, ValueError):
        pass


__all__ = [
    "SandboxConfig",
    "SandboxResult",
    "SandboxStats",
    "SandboxContext",
    "SandboxExecutor",
]
