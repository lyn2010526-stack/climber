"""AGI P5 Security Layer.

Provides enhanced Docker sandbox, resource quotas, file system isolation,
network allowlist, and security API endpoints.

Every object exported here is a live enforcement point or the live policy those
enforcement points consult:
- ``fs_isolation`` backs :class:`~app.middleware.security.PathIsolationMiddleware`
  and the docker sandbox's bind-mount checks.
- ``network_allowlist`` gates sandbox egress.
- ``quota_manager`` caps sandbox resource requests.
"""

from app.core.security.docker_sandbox import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxPolicyError,
)
from app.core.security.fs_isolation import (
    FSIsolationConfig,
    FSIsolationManager,
    fs_isolation,
)
from app.core.security.network_allowlist import NetworkAllowlist, network_allowlist
from app.core.security.resource_quotas import QuotaManager, ResourceQuota, quota_manager

__all__ = [
    "DockerSandbox",
    "DockerSandboxConfig",
    "SandboxPolicyError",
    "QuotaManager",
    "ResourceQuota",
    "quota_manager",
    "FSIsolationConfig",
    "FSIsolationManager",
    "fs_isolation",
    "NetworkAllowlist",
    "network_allowlist",
]
