"""Settings service — get-or-create and update per-user application settings."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.api_key_crypto import encrypt_api_key
from app.services import BaseService
from app.storage import async_session
from app.storage.models_platform import UserSettings

NOTIFICATION_DEFAULTS = {
    "email_address": "",
    "email_system": False,
    "email_task_done": False,
    "email_weekly": False,
    "email_marketing": False,
    "webhook_url": "",
    "webhook_task_done": False,
    "webhook_task_failed": False,
}


class _SettingsDTO:
    """Lightweight attribute container returned to the API layer."""

    def __init__(self, row: UserSettings) -> None:
        self.autonomous_agent_mode = row.autonomous_agent_mode
        self.token_throttle_mcp_enabled = row.token_throttle_mcp_enabled
        self.mcp_status = row.mcp_status
        stored = row.notifications or {}
        self.notifications = {
            key: stored.get(key, default)
            for key, default in NOTIFICATION_DEFAULTS.items() if key != "webhook_url"
        }
        self.notifications.update(webhook_url="", webhook_configured=bool(stored.get("webhook_url")))


class SettingsService(BaseService):
    """Manage per-user application settings with a persisted backing store."""

    WRITABLE_SETTINGS = frozenset({"autonomous_agent_mode", "token_throttle_mcp_enabled", "notifications"})

    @classmethod
    def validate_update(cls, data: dict[str, Any]) -> dict[str, Any]:
        unsupported = data.keys() - cls.WRITABLE_SETTINGS
        if unsupported:
            raise ValueError("包含不支持的设置字段，本次修改未保存。")
        if any(type(value) is not bool for key, value in data.items() if key != "notifications"):
            raise ValueError("设置值必须是布尔值，本次修改未保存。")
        result = dict(data)
        if "notifications" in result:
            incoming = result["notifications"]
            if not isinstance(incoming, dict) or incoming.keys() - NOTIFICATION_DEFAULTS.keys():
                raise ValueError("通知配置格式或字段无效，本次修改未保存。")
            notification = dict(incoming)
            for key, value in notification.items():
                if isinstance(NOTIFICATION_DEFAULTS[key], bool):
                    if type(value) is not bool:
                        raise ValueError("通知开关必须是布尔值，本次修改未保存。")
                else:
                    if not isinstance(value, str):
                        raise ValueError("邮件地址和 webhook URL 必须是字符串，本次修改未保存。")
                    value = value.strip()
                    if value:
                        try:
                            if key == "email_address":
                                value = str(TypeAdapter(EmailStr).validate_python(value))
                            else:
                                if len(value) > 4096 or any(char.isspace() for char in value):
                                    raise ValueError
                                TypeAdapter(AnyHttpUrl).validate_python(value)
                                url = urlsplit(value)
                                if url.username is not None or url.password is not None or url.fragment:
                                    raise ValueError
                        except ValueError:
                            label = "邮件地址" if key == "email_address" else "webhook URL（仅支持 HTTP/HTTPS，禁止用户信息和片段）"
                            raise ValueError(label + "格式无效，本次修改未保存。") from None
                    notification[key] = value
            result["notifications"] = notification
        return result

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
        notifications: dict[str, Any] | None = None,
    ) -> _SettingsDTO:
        values = self.validate_update({key: value for key, value in {
            "autonomous_agent_mode": autonomous_agent_mode,
            "token_throttle_mcp_enabled": token_throttle_mcp_enabled,
            "notifications": notifications,
        }.items() if value is not None})
        async with async_session() as db:
            row = (
                await db.execute(select(UserSettings).where(UserSettings.user_id == user_id).with_for_update())
            ).scalar_one_or_none()
            if row is None:
                row = UserSettings(user_id=user_id)
                db.add(row)
            if "notifications" in values:
                incoming = values["notifications"]
                merged = {**NOTIFICATION_DEFAULTS, **(row.notifications or {}), **incoming}
                if any(merged[key] for key in ("email_system", "email_task_done", "email_weekly", "email_marketing")) and not merged["email_address"]:
                    raise ValueError("启用邮件通知时必须填写邮件地址，本次修改未保存。")
                if (merged["webhook_task_done"] or merged["webhook_task_failed"]) and not merged["webhook_url"]:
                    raise ValueError("启用 webhook 事件时必须配置 URL，本次修改未保存。")
                if "webhook_url" in incoming:
                    merged["webhook_url"] = encrypt_api_key(incoming["webhook_url"])
                row.notifications = merged
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
