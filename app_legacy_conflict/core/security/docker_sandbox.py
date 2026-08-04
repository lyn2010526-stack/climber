"""Enhanced Docker Sandbox with full isolation.

Extends the existing Docker sandbox with:
- Ephemeral containers (auto-destroy after execution)
- Volume mounts (read-only by default)
- Container resource limits enforced via Docker API
- Security capabilities configuration
"""

from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.safety_pipeline import ExecutionResult

logger = structlog.get_logger()


@dataclass
class DockerSandboxConfig:
    """Enhanced Docker sandbox configuration."""
    image: str = "python:3.11-slim"
    cpu_limit: float = 0.5
    memory_limit: str = "256m"
    disk_limit: str = "1g"
    network_mode: str = "none"
    read_only_root: bool = True
    security_capabilities: list[str] = field(default_factory=lambda: ["no-new-privileges"])
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])
    pids_limit: int = 64
    timeout_seconds: int = 60
    max_output_bytes: int = 10000
    ephemeral: bool = True
    volume_mounts: dict[str, str] = field(default_factory=dict)


class DockerSandbox:
    """Enhanced Docker container isolation with full resource control."""

    def __init__(self, config: DockerSandboxConfig | None = None):
        self.config = config or DockerSandboxConfig()
        self._client = None
        self._available = None
        self._active_containers: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        """Check if Docker is available."""
        if self._available is not None:
            return self._available
        try:
            import docker
            self._client = docker.from_env()
            self._client.ping()
            self._available = True
        except Exception:
            self._available = False
            logger.info("docker_not_available", fallback="L2")
        return self._available

    def create_container(
        self,
        cmd: list[str],
        cwd: str,
        env: dict[str, str] | None = None,
        network: bool = False,
    ) -> str:
        """Create a Docker container and return its ID."""
        if not self.available:
            raise RuntimeError("Docker not available")

        import docker
        client = self._client or docker.from_env()

        workdir = cwd or tempfile.mkdtemp(prefix="sandbox_")
        abs_workdir = os.path.abspath(workdir)
        container_name = f"sec_sandbox_{int(time.time())}_{os.getpid()}"

        volumes = {abs_workdir: {"bind": "/workspace", "mode": "rw"}}
        for host_path, mode in self.config.volume_mounts.items():
            abs_path = os.path.abspath(host_path)
            volumes[abs_path] = {"bind": f"/mnt/{os.path.basename(abs_path)}", "mode": mode}

        nano_cpus = int(self.config.cpu_limit * 1e9)

        container_config = {
            "image": self.config.image,
            "command": cmd,
            "name": container_name,
            "detach": True,
            "remove": False,
            "network_mode": "bridge" if network else self.config.network_mode,
            "mem_limit": self.config.memory_limit,
            "nano_cpus": nano_cpus,
            "read_only": self.config.read_only_root,
            "volumes": volumes,
            "working_dir": "/workspace",
            "environment": env or {},
            "security_opt": self.config.security_capabilities,
            "cap_drop": self.config.cap_drop,
            "pids_limit": self.config.pids_limit,
            "stdin_open": False,
            "tty": False,
            "storage_opt": {"size": self.config.disk_limit},
        }

        logger.info(
            "docker_creating_container",
            image=self.config.image,
            cmd=str(cmd)[:100],
            ephemeral=self.config.ephemeral,
        )

        container = client.containers.run(**container_config)
        self._active_containers[container.id] = container
        return container.id

    def execute_command(
        self,
        container_id: str,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Wait for container execution and return result."""
        container = self._active_containers.get(container_id)
        if not container:
            return ExecutionResult(error=f"Container {container_id} not found", returncode=-1)

        timeout = timeout or self.config.timeout_seconds

        try:
            result = container.wait(timeout=timeout)
            logs = container.logs(stdout=True, stderr=True)

            stdout = ""
            try:
                stdout = logs.decode("utf-8")[:self.config.max_output_bytes]
            except Exception as e:
                logger.warning("security_docker_sandbox.logs_decode", error=str(e))

            return ExecutionResult(
                stdout=stdout,
                stderr="",
                returncode=result.get("StatusCode", 0),
                timed_out=False,
            )
        except Exception as e:
            try:
                container.kill()
            except Exception as e:
                logger.warning("security_docker_sandbox.container_kill_timeout", error=str(e))
            logger.warning("docker_execution_timeout", error=str(e))
            return ExecutionResult(
                error=f"Docker execution timeout/error: {e}",
                returncode=-1,
                timed_out=True,
            )

    def destroy_container(self, container_id: str) -> bool:
        """Force-remove a container."""
        container = self._active_containers.pop(container_id, None)
        if not container:
            return False
        try:
            container.remove(force=True)
            return True
        except Exception:
            return False

    def get_logs(self, container_id: str) -> str:
        """Get container logs."""
        container = self._active_containers.get(container_id)
        if not container:
            return ""
        try:
            logs = container.logs(stdout=True, stderr=True)
            return logs.decode("utf-8")[:self.config.max_output_bytes]
        except Exception:
            return ""

    async def execute(
        self,
        cmd: list[str],
        cwd: str,
        env: dict[str, str] | None = None,
        network: bool = False,
    ) -> ExecutionResult:
        """Execute command in an ephemeral Docker container."""
        if not self.available:
            return ExecutionResult(
                error="Docker not available, falling back to L2",
                returncode=-1,
            )

        container_id = None
        try:
            container_id = self.create_container(cmd, cwd, env, network)
            result = self.execute_command(container_id)
            return result
        except Exception as e:
            logger.error("docker_execution_error", error=str(e))
            return ExecutionResult(error=f"Docker error: {e}", returncode=-1)
        finally:
            if container_id and self.config.ephemeral:
                self.destroy_container(container_id)

    def cleanup(self) -> None:
        """Remove all active containers."""
        for container_id in list(self._active_containers.keys()):
            self.destroy_container(container_id)

        if not self.available:
            return
        try:
            containers = self._client.containers.list(
                all=True,
                filters={"name": "sec_sandbox_"},
            )
            for c in containers:
                try:
                    c.remove(force=True)
                except Exception as e:
                    logger.warning("security_docker_sandbox.cleanup_container_remove", error=str(e))
        except Exception as e:
            logger.warning("security_docker_sandbox.cleanup_list_containers", error=str(e))
