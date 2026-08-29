"""Unified Sandbox Facade — single interface to all sandbox implementations.

Provides a unified API for command execution across different sandbox backends:
- SandboxExecutor (local subprocess)
- SecuritySandbox (security-focused)
- DockerSandbox (container isolation)
- SandboxRuntime (MCP plugin)
- SessionIsolationSandbox (session-level isolation)

The facade selects the appropriate backend based on configuration and fallback logic.
"""

from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger()


class UnifiedSandbox:
    """Unified interface to all sandbox implementations.

    Usage:
        sandbox = UnifiedSandbox()
        result = await sandbox.execute("ls -la", workdir="/tmp")
    """

    def __init__(
        self,
        prefer_docker: bool = True,
        fallback_to_local: bool = True,
        timeout_seconds: int = 120,
    ):
        self.prefer_docker = prefer_docker
        self.fallback_to_local = fallback_to_local
        self.timeout_seconds = timeout_seconds
        self._local_executor = None
        self._docker_available: bool | None = None

    def _get_local_executor(self):
        """Get or create the local SandboxExecutor."""
        if self._local_executor is None:
            from app.core.sandbox import SandboxConfig, SandboxExecutor
            config = SandboxConfig(
                timeout_seconds=self.timeout_seconds,
                max_output_bytes=100000,
            )
            self._local_executor = SandboxExecutor(config)
        return self._local_executor

    async def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5)
            self._docker_available = proc.returncode == 0
        except Exception:
            self._docker_available = False

        return self._docker_available

    async def execute(
        self,
        command: str,
        workdir: str | None = None,
        timeout: int | None = None,
        use_docker: bool | None = None,
    ) -> str:
        """Execute a command in the sandbox.

        Args:
            command: Shell command to execute
            workdir: Working directory (optional)
            timeout: Timeout in seconds (optional, uses default if not set)
            use_docker: Force Docker usage (None = auto-detect)

        Returns:
            Command output as string
        """
        effective_timeout = timeout or self.timeout_seconds

        # Determine which backend to use
        should_use_docker = use_docker
        if should_use_docker is None:
            should_use_docker = self.prefer_docker and await self._check_docker_available()

        # Try Docker first if preferred
        if should_use_docker:
            try:
                return await self._execute_docker(command, workdir, effective_timeout)
            except Exception as e:
                logger.warning(
                    "unified_sandbox.docker_failed_fallback",
                    error=str(e),
                )
                if not self.fallback_to_local:
                    raise

        # Fall back to local execution
        return await self._execute_local(command, workdir, effective_timeout)

    async def _execute_local(
        self,
        command: str,
        workdir: str | None,
        timeout: int,
    ) -> str:
        """Execute command using local SandboxExecutor."""
        executor = self._get_local_executor()
        return await executor.execute(command, timeout=timeout)

    async def _execute_docker(
        self,
        command: str,
        workdir: str | None,
        timeout: int,
    ) -> str:
        """Execute command using Docker sandbox."""
        from app.core.docker_sandbox import DockerSandbox, DockerSandboxConfig

        config = DockerSandboxConfig(
            image="python:3.11-slim",
            timeout_seconds=timeout,
            workdir=workdir or "/workspace",
        )

        async with DockerSandbox(config) as sandbox:
            return await sandbox.execute(command)

    async def execute_with_validation(
        self,
        command: str,
        workdir: str | None = None,
        timeout: int | None = None,
    ) -> tuple[bool, str]:
        """Execute command with pre-validation against hazard patterns.

        Returns:
            Tuple of (success, output)
        """
        from app.core.security_sandbox import validate_command_allowlist

        allowed, reason = validate_command_allowlist(command)
        if not allowed:
            return False, f"Command blocked: {reason}"

        try:
            output = await self.execute(command, workdir, timeout)
            return True, output
        except Exception as e:
            return False, f"Execution error: {e}"

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._local_executor:
            self._local_executor.cleanup()
            self._local_executor = None
