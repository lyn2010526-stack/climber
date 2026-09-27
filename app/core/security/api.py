"""Security API endpoints.

Provides REST endpoints for managing security configuration:
- Resource quotas
- File system isolation config
- Network allowlist

All endpoints require admin authentication, because each one mutates or
discloses the live isolation policy used by the request middleware and the
docker sandbox. Mounted from ``app.main``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth_manager import require_admin
from app.core.security.fs_isolation import fs_isolation
from app.core.security.network_allowlist import network_allowlist
from app.core.security.resource_quotas import ResourceQuota, quota_manager

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


@router.get("/quotas", dependencies=[Depends(require_admin())])
async def get_quotas() -> dict[str, Any]:
    return {
        "quotas": quota_manager.get_all_quotas(),
        "usage": quota_manager.get_all_usage(),
    }


@router.put("/quotas", dependencies=[Depends(require_admin())])
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


def _fs_config_payload() -> dict[str, Any]:
    config = fs_isolation.config
    return {
        "allowed_paths": config.allowed_paths,
        "blocked_paths": config.blocked_paths,
        "read_only_paths": config.read_only_paths,
        "max_file_size_mb": config.max_file_size_mb,
        "allowed_extensions": config.allowed_extensions,
    }


@router.get("/fs-config", dependencies=[Depends(require_admin())])
async def get_fs_config() -> dict[str, Any]:
    return _fs_config_payload()


@router.put("/fs-config", dependencies=[Depends(require_admin())])
async def update_fs_config(
    request: FSConfigRequest,
) -> dict[str, Any]:
    """Replace the live filesystem-isolation policy.

    Mutates the process-wide ``fs_isolation`` policy object so the change
    applies immediately to the request middleware and the docker sandbox.
    Fields left at their empty defaults keep their current value, because an
    empty ``blocked_paths`` or ``allowed_extensions`` would silently disable
    the corresponding check.
    """
    config = fs_isolation.config
    if request.allowed_paths:
        config.allowed_paths = list(request.allowed_paths)
    if request.blocked_paths:
        config.blocked_paths = list(request.blocked_paths)
    if request.read_only_paths:
        config.read_only_paths = list(request.read_only_paths)
    if request.max_file_size_mb > 0:
        config.max_file_size_mb = request.max_file_size_mb
    if request.allowed_extensions:
        config.allowed_extensions = list(request.allowed_extensions)
    return {"status": "updated", "config": _fs_config_payload()}


# --- Network Allowlist Endpoints ---


@router.get("/network-allowlist", dependencies=[Depends(require_admin())])
async def get_network_allowlist() -> dict[str, Any]:
    return {
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }


@router.post("/network-allowlist", dependencies=[Depends(require_admin())])
async def add_to_allowlist(
    request: DomainRequest,
) -> dict[str, Any]:
    network_allowlist.add_allowed_domain(request.domain)
    return {
        "status": "added",
        "domain": request.domain,
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }


@router.delete("/network-allowlist/{domain}", dependencies=[Depends(require_admin())])
async def remove_from_allowlist(
    domain: str,
) -> dict[str, Any]:
    network_allowlist.remove_allowed_domain(domain)
    return {
        "status": "removed",
        "domain": domain,
        "allowed_domains": network_allowlist.get_allowed_domains(),
    }
