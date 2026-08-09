"""Resource Quota Management.

Provides per-agent resource quota tracking and enforcement:
- CPU cores limit
- Memory (MB) limit
- Disk (MB) limit
- Network bandwidth (kbps) limit
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class ResourceQuota:
    """Resource quota configuration."""
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 1024
    network_kbps: int = 10000


@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""
    cpu_seconds: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_kb: float = 0.0
    timestamp: float = field(default_factory=time.time)


class QuotaExceededError(Exception):
    """Raised when a resource quota is exceeded."""


class QuotaManager:
    """Manages resource quotas per agent."""

    DEFAULT_QUOTA = ResourceQuota(
        cpu_cores=2.0,
        memory_mb=1024,
        disk_mb=2048,
        network_kbps=50000,
    )

    def __init__(self, default_quota: ResourceQuota | None = None):
        self._default_quota = default_quota or self.DEFAULT_QUOTA
        self._agent_quotas: dict[str, ResourceQuota] = {}
        self._agent_usage: dict[str, ResourceUsage] = {}
        self._lock = Lock()

    def set_quota(self, agent_id: str, quota: ResourceQuota) -> None:
        """Set quota for a specific agent."""
        with self._lock:
            self._agent_quotas[agent_id] = quota
            logger.info("quota_set", agent_id=agent_id, quota=quota)

    def get_quota(self, agent_id: str) -> ResourceQuota:
        """Get quota for an agent (falls back to default)."""
        return self._agent_quotas.get(agent_id, self._default_quota)

    def check_quota(self, agent_id: str, usage: ResourceUsage) -> tuple[bool, str]:
        """Check if usage is within quota. Returns (ok, reason)."""
        quota = self.get_quota(agent_id)

        if usage.memory_mb > quota.memory_mb:
            return False, f"Memory quota exceeded: {usage.memory_mb:.0f}MB > {quota.memory_mb}MB"
        if usage.disk_mb > quota.disk_mb:
            return False, f"Disk quota exceeded: {usage.disk_mb:.0f}MB > {quota.disk_mb}MB"
        if usage.network_kb * 8 > quota.network_kbps:
            return False, f"Network quota exceeded: {usage.network_kb * 8:.0f}kbps > {quota.network_kbps}kbps"

        return True, ""

    def enforce_quota(self, agent_id: str, usage: ResourceUsage) -> None:
        """Raise QuotaExceededError if usage exceeds quota."""
        ok, reason = self.check_quota(agent_id, usage)
        if not ok:
            logger.warning("quota_exceeded", agent_id=agent_id, reason=reason)
            raise QuotaExceededError(reason)

    def record_usage(self, agent_id: str, usage: ResourceUsage) -> None:
        """Record usage and enforce quota."""
        with self._lock:
            self._agent_usage[agent_id] = usage
        self.enforce_quota(agent_id, usage)

    def get_usage(self, agent_id: str) -> ResourceUsage | None:
        """Get current usage for an agent."""
        return self._agent_usage.get(agent_id)

    def reset_usage(self, agent_id: str) -> None:
        """Reset usage tracking for an agent."""
        with self._lock:
            self._agent_usage.pop(agent_id, None)

    def remove_agent(self, agent_id: str) -> None:
        """Remove all quota and usage data for an agent."""
        with self._lock:
            self._agent_quotas.pop(agent_id, None)
            self._agent_usage.pop(agent_id, None)

    def get_all_quotas(self) -> dict[str, dict[str, Any]]:
        """Get all agent quotas as dict."""
        result = {"_default": self._quota_to_dict(self._default_quota)}
        for agent_id, quota in self._agent_quotas.items():
            result[agent_id] = self._quota_to_dict(quota)
        return result

    def get_all_usage(self) -> dict[str, dict[str, Any]]:
        """Get all agent usage as dict."""
        result = {}
        for agent_id, usage in self._agent_usage.items():
            result[agent_id] = {
                "cpu_seconds": usage.cpu_seconds,
                "memory_mb": usage.memory_mb,
                "disk_mb": usage.disk_mb,
                "network_kb": usage.network_kb,
                "timestamp": usage.timestamp,
            }
        return result

    @staticmethod
    def _quota_to_dict(quota: ResourceQuota) -> dict[str, Any]:
        return {
            "cpu_cores": quota.cpu_cores,
            "memory_mb": quota.memory_mb,
            "disk_mb": quota.disk_mb,
            "network_kbps": quota.network_kbps,
        }


quota_manager = QuotaManager()
