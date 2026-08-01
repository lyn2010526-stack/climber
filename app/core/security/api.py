"""Security API endpoints.

Provides REST endpoints for managing security configuration:
- Resource quotas
- File system isolation config
- Network allowlist
All endpoints require admin authentication.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.security.docker_sandbox import DockerSandboxConfig
from app.core.security.fs_isolation import FSIsolationConfig, FSIsolationManager
from app.core.security.network_allowlist import NetworkAllowlist, network_allowlist
from app.core.security.resource_quotas import QuotaManager, ResourceQuota, quota_manager
router = APIRouter(prefix="/api/v1/security", tags=["security"])


# --- Request/Response Models ---


class QuotaRequest(BaseModel):
    agent_id: str
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 1024
    network_kbps: int = 10000


class FSConfigRequest(BaseModel):
    allowed_paths: list[str] = []
    blocked_paths: list[str] = []
    read_only_paths: list[str] = []
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = []


class DomainRequest(BaseModel):
    domain: str


# --- Quota Endpoints ---


@router.get("/quotas")
async def get_quotas() -> dict[str, Any]:
    return {
        "quotas": quota_manager.get_all_quotas(),
        "usage": quota_manager.get_all_usage(),
    }


@router.put("/quotas")
async def update_quota(
    request: QuotaRequest,
) -> dict[str, Any]:
    quota = ResourceQuota(
        cpu_cores=request.cpu_cores,
        memory_mb=request.memory_mb,
        disk_mb=request.disk_mb,
        network_kbps=request.network_kbps,
    )
    quota_manager.set_quota(request.agent_id, quota)
    return {"status": "updated", "agent_id": request.agent_id, "quota": quota_manager._quota_to_dict(quota)}


# --- FS Config Endpoints ---


@router.get("/fs-config")
async def get_fs_config() -> dict[str, Any]:
    config = FSIsolationManager().config
    return {
        "allowed_paths": config.allowed_paths,
        "blocked_paths": config.blocked_paths,
        "read_only_paths": config.read_only_paths,
        "max_file_size_mb": config.max_file_size_mb,
        "allowed_extensions": config.allowed_extensions,
    }


@router.put("/fs-config")
async def update_fs_config(
    request: FSConfigRequest,
) -> dict[str, Any]:
    config = FSIsolationConfig(
        allowed_paths=request.allowed_paths,
        blocked_paths=request.blocked_paths,
        read_only_paths=request.read_only_paths,
        max_file_size_mb=request.max_file_size_mb,
        allowed_extensions=request.allowed_extensions,
    )
    manager = FSIsolationManager(config)
    return {"status": "updated", "config": {
        "allowed_paths": manager.config.allowed_paths,
        "blocked_paths": manager.config.blocked_paths,
        "read_only_paths": manager.config.read_only_paths,
    }}


# --- Network Allowlist Endpoints ---


@router.get("/network-allowlist")
async def get_network_allowlist() -> dict[str, Any]:
    return {
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }


@router.post("/network-allowlist")
async def add_to_allowlist(
    request: DomainRequest,
) -> dict[str, Any]:
    network_allowlist.add_allowed_domain(request.domain)
    return {
        "status": "added",
        "domain": request.domain,
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }


@router.delete("/network-allowlist/{domain}")
async def remove_from_allowlist(
    domain: str,
) -> dict[str, Any]:
    network_allowlist.remove_allowed_domain(domain)
    return {
        "status": "removed",
        "domain": domain,
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }
