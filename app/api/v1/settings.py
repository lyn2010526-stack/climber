"""Settings API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_manager import require_scopes
from app.core.principal import CurrentPrincipal
from app.services.settings_service import SettingsService
from app.storage import get_db

router = APIRouter(tags=["settings"])


@router.get("/")
async def get_settings(
    principal: CurrentPrincipal,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current user settings."""
    service = SettingsService(db)
    settings = await service.get_settings(principal.subject_id)
    mode = service.get_effective_mode(settings)

    return {
        "autonomous_agent_mode": settings.autonomous_agent_mode,
        "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
        "mcp_status": settings.mcp_status,
        "mcp_ready": settings.mcp_status == "ready",
        "notifications": settings.notifications,
        "notification_delivery_available": False,
        **mode,
    }


@router.patch("/")
async def update_settings(
    principal: CurrentPrincipal,
    data: dict[str, Any],
    _auth: dict = Depends(require_scopes("write")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update user settings."""
    service = SettingsService(db)
    try:
        data = service.validate_update(data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    autonomous_agent_mode = data.get("autonomous_agent_mode")
    token_throttle_mcp_enabled = data.get("token_throttle_mcp_enabled")

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one setting must be provided",
        )

    try:
        settings = await service.update_settings(
            user_id=principal.subject_id,
            autonomous_agent_mode=autonomous_agent_mode,
            token_throttle_mcp_enabled=token_throttle_mcp_enabled,
            notifications=data.get("notifications"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    mode = service.get_effective_mode(settings)

    return {
        "autonomous_agent_mode": settings.autonomous_agent_mode,
        "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
        "mcp_status": settings.mcp_status,
        "mcp_ready": settings.mcp_status == "ready",
        "notifications": settings.notifications,
        "notification_delivery_available": False,
        **mode,
    }
