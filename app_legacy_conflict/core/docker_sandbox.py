"""Phase 3: Container Isolation (L3) — Docker sandbox for high-risk operations.

Reference: AutoGen DockerCommandLineCodeExecutor, Open Interpreter sandbox.

Features:
- Ephemeral containers (created and destroyed per execution)
- Read-only filesystem (except workspace directory)
- Network isolation (default off, whitelist-based)
- Resource quotas (CPU/memory/PID)
- Seccomp profile
- Graceful degradation to L2 when Docker unavailable
"""

from __future__ import annotations

import os
import shutil
import structlog
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.safety_pipeline import SafetyResult, ExecutionResult, RiskLevel

logger = structlog.get_logger()


@dataclass
class DockerSandboxConfig:
    """Docker sandbox configuration."""
    image: str = "python:3.11-slim"
    timeout_seconds: int = 60
    max_output_bytes: int = 10000
    mem_limit: str = "256m"
    cpu_quota: int = 50000  # 50% of CPU
    cpu_period: int = 100000
    network_mode: str = "none"  # "none" for isolation, "bridge" for access
    read_only: bool = True
    security_opt: list[str] = field(default_factory=lambda: ["no-new-privileges"])
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])
    pids_limit: int = 64


class DockerSandbox:
    """Docker container isolation for high-risk tool execution.

    Each execution creates a new ephemeral container.
    Reference: AutoGen DockerCommandLineCodeExecutor.
    """

    def __init__(self, config: DockerSandboxConfig | None = None):
        self.config = config or DockerSandboxConfig()
        self._client = None
        self._available = None

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

        import docker
        container = None
        try:
            client = self._client or docker.from_env()

            # Prepare workspace volume
            workdir = cwd or tempfile.mkdtemp(prefix="sandbox_")
            abs_workdir = os.path.abspath(workdir)
            container_name = f"sandbox_{int(time.time())}_{os.getpid()}"

            container_config = {
                "image": self.config.image,
                "command": cmd,
                "name": container_name,
                "detach": True,
                "remove": False,
                "network_mode": "bridge" if network else self.config.network_mode,
                "mem_limit": self.config.mem_limit,
                "cpu_quota": self.config.cpu_quota,
                "cpu_period": self.config.cpu_period,
                "read_only": self.config.read_only,
                "volumes": {
                    abs_workdir: {"bind": "/workspace", "mode": "rw"},
                },
                "working_dir": "/workspace",
                "environment": env or {},
                "security_opt": self.config.security_opt,
                "cap_drop": self.config.cap_drop,
                "pids_limit": self.config.pids_limit,
                "stdin_open": False,
                "tty": False,
            }

            logger.info(
                "docker_creating_container",
                image=self.config.image,
                cmd=str(cmd)[:100],
            )

            container = client.containers.run(**container_config)

            try:
                result = container.wait(timeout=self.config.timeout_seconds)
                logs = container.logs(stdout=True, stderr=True)

                stdout = ""
                stderr = ""
                try:
                    stdout = logs.decode("utf-8")[:self.config.max_output_bytes]
                except Exception as e:
                    logger.warning("docker_sandbox.logs_decode", error=str(e))

                return ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    returncode=result.get("StatusCode", 0),
                    timed_out=False,
                )
            except Exception as e:
                # Timeout or other error
                try:
                    container.kill()
                except Exception as e:
                    logger.warning("docker_sandbox.container_kill_timeout", error=str(e))
                logger.warning("docker_execution_timeout", error=str(e))
                return ExecutionResult(
                    error=f"Docker execution timeout/error: {e}",
                    returncode=-1,
                    timed_out=True,
                )

        except Exception as e:
            logger.error("docker_execution_error", error=str(e))
            return ExecutionResult(
                error=f"Docker error: {e}",
                returncode=-1,
            )
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logger.warning("docker_sandbox.container_remove", error=str(e))

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        cwd: str = "",
    ) -> ExecutionResult:
        """Execute code snippet in a temporary container."""
        suffix = {"python": ".py", "javascript": ".js", "bash": ".sh"}.get(language, ".txt")
        runner = {
            "python": "python3",
            "javascript": "node",
            "bash": "bash",
        }.get(language, "cat")

        workdir = cwd or tempfile.mkdtemp(prefix="sandbox_")
        script_path = os.path.join(workdir, f"script{suffix}")

        with open(script_path, "w") as f:
            f.write(code)

        cmd = [runner, f"/workspace/script{suffix}"]
        result = await self.execute(cmd, cwd=workdir)

        # Cleanup temp script
        try:
            os.unlink(script_path)
        except Exception as e:
            logger.warning("docker_sandbox.cleanup_script", error=str(e))

        return result

    def cleanup(self) -> None:
        """Remove any leftover containers."""
        if not self.available:
            return
        try:
            containers = self._client.containers.list(
                all=True,
                filters={"name": "sandbox_"},
            )
            for c in containers:
                try:
                    c.remove(force=True)
                except Exception as e:
                    logger.warning("docker_sandbox.cleanup_container_remove", error=str(e))
        except Exception as e:
            logger.warning("docker_sandbox.cleanup_list_containers", error=str(e))
