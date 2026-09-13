"""Settings service — get-or-create and update per-user application settings."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.services import BaseService
from app.storage import async_session
from app.storage.models_platform import UserSettings


class _SettingsDTO:
    """Lightweight attribute container returned to the API layer."""

    def __init__(self, row: UserSettings) -> None:
        self.autonomous_agent_mode = row.autonomous_agent_mode
        self.token_throttle_mcp_enabled = row.token_throttle_mcp_enabled
        self.mcp_status = row.mcp_status


class SettingsService(BaseService):
    """Manage per-user application settings with a persisted backing store."""

    async def get_settings(self, user_id: str) -> _SettingsDTO:
        async with async_session() as db:
            row = (
                await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            ).scalar_one_or_none()
            if row is None:
                row = UserSettings(user_id=user_id)
                db.add(row)
                await db.commit()
                await db.refresh(row)
            return _SettingsDTO(row)

    async def update_settings(
        self,
        user_id: str,
        autonomous_agent_mode: bool | None = None,
        token_throttle_mcp_enabled: bool | None = None,
    ) -> _SettingsDTO:
        async with async_session() as db:
            row = (
                await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            ).scalar_one_or_none()
            if row is None:
                row = UserSettings(user_id=user_id)
                db.add(row)
            if autonomous_agent_mode is not None:
                row.autonomous_agent_mode = bool(autonomous_agent_mode)
            if token_throttle_mcp_enabled is not None:
                row.token_throttle_mcp_enabled = bool(token_throttle_mcp_enabled)
            await db.commit()
            await db.refresh(row)
            return _SettingsDTO(row)

    def get_effective_mode(self, settings: _SettingsDTO) -> dict[str, Any]:
        """Derive the effective agent mode from the stored settings."""
        return {"mode": "auto" if settings.autonomous_agent_mode else "manual"}
