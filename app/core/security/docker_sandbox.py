"""Enhanced Docker Sandbox with full isolation.

Extends the existing Docker sandbox with:
- Ephemeral containers (auto-destroy after execution)
- Volume mounts (read-only by default)
- Container resource limits enforced via Docker API
- Security capabilities configuration

Isolation policy is **fail-closed**: the ``DockerSandboxConfig`` is the policy
and a call-site flag can only narrow it. A request for network access is
refused unless the configured ``network_mode`` already permits it *and* every
egress target passes the shared network allowlist. Host paths are checked
against the shared filesystem-isolation policy before they are bind-mounted,
and requested resource limits are checked against the per-agent quota.
"""

from __future__ import annotations

import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.security.fs_isolation import fs_isolation
from app.core.security.network_allowlist import network_allowlist
from app.core.security.resource_quotas import (
    ResourceUsage,
    quota_manager,
)

logger = structlog.get_logger()

# Network modes that hand the container the host's network namespace. Refused
# outright: a sandboxed process must not reach host-local services or cloud
# metadata endpoints.
FORBIDDEN_NETWORK_MODES = frozenset({"host"})

# Docker graph drivers whose backing filesystem honours ``storage_opt.size``.
# Anything else silently ignores the per-container disk cap, so a requested
# ``disk_limit`` is refused rather than quietly unenforced.
STORAGE_DRIVERS_WITH_DISK_QUOTA = frozenset(
    {"overlay2", "btrfs", "zfs", "windowsfilter"}
)

_SIZE_UNITS = {"k": 1 / 1024, "m": 1, "g": 1024, "t": 1024 * 1024}
_SIZE_PATTERN = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([kmgt]?)b?\s*$", re.IGNORECASE)

ALLOWED_MOUNT_MODES = frozenset({"ro", "rw"})


class SandboxPolicyError(RuntimeError):
    """A sandbox request violated the configured isolation policy.

    Raised instead of degrading quietly, so a caller can never mistake a
    refused container for an isolated one.
    """


@dataclass
class ExecutionResult:
    """Outcome of a sandboxed command."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    error: str | None = None
    timed_out: bool = False


def parse_size_mb(value: str) -> float:
    """Parse a Docker size string (``"256m"``, ``"1g"``, ``"512"``) into MB."""
    match = _SIZE_PATTERN.match(value or "")
    if not match:
        raise ValueError(f"Unparsable size value: {value!r}")
    magnitude, unit = match.groups()
    return float(magnitude) * _SIZE_UNITS.get(unit.lower(), 1)


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
    # Egress destinations the sandbox may reach when network access is
    # granted. Empty means "no destination is authorised", so flipping
    # ``network=True`` alone can never open egress.
    allowed_network_hosts: list[str] = field(default_factory=list)


class DockerSandbox:
    """Enhanced Docker container isolation with full resource control."""

    def __init__(self, config: DockerSandboxConfig | None = None):
        self.config = config or DockerSandboxConfig()
        self._client = None
        self._available = None
        self._storage_driver: str | None = None
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

    def _require_client(self) -> Any:
        if not self.available:
            raise SandboxPolicyError("Docker not available")
        return self._client

    # ── Policy enforcement ──────────────────────────────────────────────

    def resolve_network_mode(self, network: bool) -> str:
        """Return the Docker ``network_mode`` for this run.

        The configured ``network_mode`` is the ceiling. ``network=False``
        always yields ``"none"``; ``network=True`` yields the configured mode
        only when that mode permits egress and every declared host passes the
        network allowlist. There is no input that widens the policy.
        """
        policy = (self.config.network_mode or "none").strip().lower()

        if policy in FORBIDDEN_NETWORK_MODES:
            raise SandboxPolicyError(
                f"network_mode={policy!r} is refused for sandboxed execution: it shares the "
                "host network namespace. Use a dedicated bridge network plus an egress proxy."
            )

        if not network:
            return "none"

        if policy == "none":
            raise SandboxPolicyError(
                "network access was requested but DockerSandboxConfig.network_mode is 'none'. "
                "Set network_mode explicitly (for example 'bridge') to permit egress; the "
                "per-call flag cannot widen the policy."
            )

        self.assert_egress_allowed()
        return policy

    def assert_egress_allowed(self) -> None:
        """Require every declared egress host to pass the network allowlist."""
        hosts = self.config.allowed_network_hosts
        if not hosts:
            raise SandboxPolicyError(
                "network access was requested with no allowed_network_hosts configured, so no "
                "destination is authorised. Populate DockerSandboxConfig.allowed_network_hosts."
            )

        rejected: list[str] = []
        for host in hosts:
            url = host if "://" in host else f"https://{host}"
            ok, reason = network_allowlist.check_url(url)
            if not ok:
                rejected.append(f"{host}: {reason}")
        if rejected:
            raise SandboxPolicyError(
                "egress refused by the network allowlist — " + "; ".join(rejected)
            )

    def assert_disk_quota_supported(self) -> None:
        """Refuse a disk cap the Docker storage driver cannot enforce."""
        if not self.config.disk_limit:
            return

        driver = self.storage_driver()
        if driver not in STORAGE_DRIVERS_WITH_DISK_QUOTA:
            supported = ", ".join(sorted(STORAGE_DRIVERS_WITH_DISK_QUOTA))
            raise SandboxPolicyError(
                f"disk_limit={self.config.disk_limit!r} requires a storage driver that enforces "
                f"per-container size quotas, but Docker reports Driver={driver!r}. "
                f"Drivers with quota support: {supported}. Switch the driver or set "
                "disk_limit='' to run the sandbox without a disk cap."
            )

    def storage_driver(self) -> str:
        """Report the Docker graph driver name (cached for the sandbox lifetime)."""
        if self._storage_driver is not None:
            return self._storage_driver

        client = self._require_client()
        try:
            info = client.info() or {}
            driver = str(info.get("Driver") or "").strip().lower()
        except Exception as exc:
            raise SandboxPolicyError(
                f"cannot verify Docker storage driver support for disk_limit="
                f"{self.config.disk_limit!r}: {exc}"
            ) from exc

        if not driver:
            raise SandboxPolicyError(
                f"cannot verify Docker storage driver support for disk_limit="
                f"{self.config.disk_limit!r}: Docker reported no Driver"
            )

        self._storage_driver = driver
        return driver

    def assert_paths_allowed(self, workdir: str) -> str:
        """Validate the working directory and every configured bind mount."""
        mounts = self.config.volume_mounts
        candidates: list[tuple[str, str]] = [("sandbox workdir", workdir)]
        candidates.extend((f"volume mount {host_path!r}", host_path) for host_path in mounts)

        for label, path in candidates:
            if not path:
                raise SandboxPolicyError(f"{label} is empty")
            try:
                fs_isolation.assert_allowed(path, purpose=label)
            except ValueError as exc:
                raise SandboxPolicyError(str(exc)) from exc

        for host_path, mode in mounts.items():
            normalized = (mode or "").strip().lower()
            if normalized not in ALLOWED_MOUNT_MODES:
                raise SandboxPolicyError(
                    f"volume mount {host_path!r} requests mode {mode!r}; allowed modes are "
                    f"{sorted(ALLOWED_MOUNT_MODES)}"
                )

        return os.path.abspath(workdir)

    def assert_within_quota(self, agent_id: str) -> None:
        """Refuse limits that exceed the agent's configured resource quota."""
        try:
            requested = ResourceUsage(
                memory_mb=parse_size_mb(self.config.memory_limit),
                disk_mb=parse_size_mb(self.config.disk_limit) if self.config.disk_limit else 0.0,
            )
        except ValueError as exc:
            raise SandboxPolicyError(f"unparsable sandbox resource limit: {exc}") from exc

        ok, reason = quota_manager.check_quota(agent_id, requested)
        if not ok:
            raise SandboxPolicyError(
                f"sandbox resource request exceeds the quota for agent {agent_id or '(default)'}: {reason}"
            )

    # ── Container lifecycle ─────────────────────────────────────────────

    def create_container(
        self,
        cmd: list[str],
        cwd: str,
        env: dict[str, str] | None = None,
        network: bool = False,
        agent_id: str = "",
    ) -> str:
        """Create a Docker container and return its ID."""
        client = self._require_client()

        raw_workdir = cwd or tempfile.mkdtemp(prefix="sandbox_")
        abs_workdir = self.assert_paths_allowed(raw_workdir)
        network_mode = self.resolve_network_mode(network)
        self.assert_disk_quota_supported()
        self.assert_within_quota(agent_id)

        container_name = f"sec_sandbox_{int(time.time())}_{os.getpid()}"

        volumes = {abs_workdir: {"bind": "/workspace", "mode": "rw"}}
        for host_path, mode in self.config.volume_mounts.items():
            # Reuse the path that passed realpath, blocked-path, and allowlist
            # checks. Re-resolving with abspath here could reintroduce a link
            # or traversal path after validation.
            resolved_path = fs_isolation.assert_allowed(
                host_path, purpose=f"volume mount {host_path!r}"
            )
            volumes[resolved_path] = {
                "bind": f"/mnt/{os.path.basename(resolved_path)}",
                "mode": mode,
            }

        nano_cpus = int(self.config.cpu_limit * 1e9)

        container_config = {
            "image": self.config.image,
            "command": cmd,
            "name": container_name,
            "detach": True,
            "remove": False,
            "network_mode": network_mode,
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
        }
        if self.config.disk_limit:
            container_config["storage_opt"] = {"size": self.config.disk_limit}

        logger.info(
            "docker_creating_container",
            image=self.config.image,
            cmd=str(cmd)[:100],
            ephemeral=self.config.ephemeral,
            network_mode=network_mode,
            agent_id=agent_id or None,
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
        agent_id: str = "",
        session_id: str = "",
    ) -> ExecutionResult:
        """Execute command in an ephemeral Docker container.

        Policy refusals raise :class:`SandboxPolicyError` after being recorded
        in the durable audit chain; a policy refusal is never reported as a
        normal command result.
        """
        from app.core.observability.audit import audit_chain

        if not self.available:
            return ExecutionResult(
                error="Docker not available, falling back to L2",
                returncode=-1,
            )

        container_id = None
        try:
            container_id = self.create_container(cmd, cwd, env, network, agent_id=agent_id)
            result = self.execute_command(container_id)
            await audit_chain.log_security_decision(
                decision_type="sandbox_execute",
                allowed=True,
                reason="isolation policy satisfied",
                subject=" ".join(cmd)[:200],
                agent_id=agent_id,
                session_id=session_id,
            )
            return result
        except SandboxPolicyError as exc:
            await audit_chain.log_security_decision(
                decision_type="sandbox_execute",
                allowed=False,
                reason=str(exc),
                subject=" ".join(cmd)[:200],
                agent_id=agent_id,
                session_id=session_id,
            )
            raise
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
