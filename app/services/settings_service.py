"""Settings service for agent mode and MCP control."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models_settings import McpStatus, UserSettings


class SettingsService:
    """Service for managing user settings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_settings(self, user_id: str) -> UserSettings:
        """Get user settings, create default if not exists."""
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSettings(
                id=str(uuid4()),
                user_id=user_id,
                autonomous_agent_mode=False,
                token_throttle_mcp_enabled=False,
                mcp_status=McpStatus.DISCONNECTED,
            )
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)

        return settings

    async def update_settings(
        self,
        user_id: str,
        autonomous_agent_mode: Optional[bool] = None,
        token_throttle_mcp_enabled: Optional[bool] = None,
    ) -> UserSettings:
        """Update user settings."""
        settings = await self.get_settings(user_id)

        if autonomous_agent_mode is not None:
            settings.autonomous_agent_mode = autonomous_agent_mode
        if token_throttle_mcp_enabled is not None:
            settings.token_throttle_mcp_enabled = token_throttle_mcp_enabled

        settings.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(settings)

        return settings

    async def update_mcp_status(self, user_id: str, status: McpStatus) -> None:
        """Update MCP status for user."""
        settings = await self.get_settings(user_id)
        settings.mcp_status = status
        settings.updated_at = datetime.utcnow()
        await self.db.commit()

    def get_effective_mode(self, settings: UserSettings) -> dict:
        """Get effective running mode based on settings."""
        return {
            "autonomous_agent_mode": settings.autonomous_agent_mode,
            "token_throttle_mcp_enabled": settings.token_throttle_mcp_enabled,
            "mcp_status": settings.mcp_status.value,
            "mcp_ready": settings.mcp_status == McpStatus.READY,
        }
