"""Settings API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.services.settings_service import SettingsService
from app.storage import get_db

router = APIRouter(tags=["settings"], dependencies=[Depends(get_current_user)])


@router.get("")
@router.get("/")
async def get_settings(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current user settings."""
    service = SettingsService(db)
    settings = await service.get_settings("default-user")
    mode = service.get_effective_mode(settings)

    return {
        "autonomous_agent_mode": settings.autonomous_agent_mode,
        "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
        "mcp_status": settings.mcp_status.value,
        **mode,
    }


@router.patch("")
@router.patch("/")
async def update_settings(
    data: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update user settings."""
    service = SettingsService(db)

    autonomous_agent_mode = data.get("autonomous_agent_mode")
    token_throttle_mcp_enabled = data.get("token_throttle_mcp_enabled")

    if autonomous_agent_mode is None and token_throttle_mcp_enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one setting must be provided",
        )

    settings = await service.update_settings(
        user_id="default-user",
        autonomous_agent_mode=autonomous_agent_mode,
        token_throttle_mcp_enabled=token_throttle_mcp_enabled,
    )

    mode = service.get_effective_mode(settings)

    return {
        "autonomous_agent_mode": settings.autonomous_agent_mode,
        "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
        "mcp_status": settings.mcp_status.value,
        **mode,
    }
