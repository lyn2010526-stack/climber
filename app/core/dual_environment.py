"""Dual environment execution strategy.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EnvironmentMode(Enum):
    LOCAL = "local"
    CONTAINER = "container"


@dataclass
class EnvironmentConfig:
    mode: EnvironmentMode = EnvironmentMode.LOCAL
    container_name: str | None = None
    workdir: str = "/tmp/sandbox"
    max_file_size_mb: int = 50
    max_output_size_kb: int = 500
    command_timeout_seconds: int = 120
    enable_network: bool = False


class DualEnvironmentExecutor:
    """Execute commands in local or container environment.

    """

    def __init__(self, config: EnvironmentConfig | None = None):
        self.config = config or EnvironmentConfig()
        self._container_available = self._check_container()

    def _check_container(self) -> bool:
        try:
            import subprocess
            result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    async def execute(self, command: str, workdir: str | None = None) -> str:
        """Execute a command in the configured environment."""
        if self.config.mode == EnvironmentMode.CONTAINER and self._container_available:
            return await self._execute_container(command, workdir)
        return await self._execute_local(command, workdir)

    async def _execute_local(self, command: str, workdir: str | None = None) -> str:
        from app.tools.builtins import stream_command
        return await stream_command(command, timeout=self.config.command_timeout_seconds, workdir=workdir or self.config.workdir)

    async def _execute_container(self, command: str, workdir: str | None = None) -> str:
        if not self.config.container_name:
            return "Error: No container configured"
        from app.tools.builtins import container_exec
        return await container_exec(self.config.container_name, command, workdir=workdir or self.config.workdir)

    def switch_mode(self, mode: EnvironmentMode) -> None:
        self.config.mode = mode
        logger.info("environment_mode_switched", mode=mode.value)


dual_environment_executor = DualEnvironmentExecutor()
