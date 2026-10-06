"""Notification service for Climber.

Provides a simple interface to fire desktop notifications from anywhere in
the backend, plus best-effort delivery through per-user webhook and email
channels once they are configured in the settings store. All calls are
best-effort: failures are logged and swallowed.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

import httpx
import structlog
from sqlalchemy import select

from app.core.api_key_crypto import decrypt_api_key
from app.storage import async_session
from app.storage.models_platform import UserSettings
from app.utils.notifications import anotify, desktop_notify_available

logger = structlog.get_logger()

WEBHOOK_DELIVERY_TIMEOUT = 10.0

# Email delivery needs an SMTP server; without SMTP_* env the email channel is
# reported unavailable instead of failing at send time.
SMTP_CONFIGURED = bool(os.getenv("SMTP_HOST"))


def compute_delivery_availability(notifications: dict[str, Any] | None) -> dict[str, bool]:
    """Derive which delivery channels are usable from stored settings."""
    notifications = notifications or {}
    email_address = str(notifications.get("email_address") or "")
    webhook_configured = bool(
        notifications.get("webhook_configured") or notifications.get("webhook_url")
    )
    channel_status = {
        "desktop": desktop_notify_available(),
        "webhook": webhook_configured,
        "email": bool(email_address) and SMTP_CONFIGURED,
    }
    channel_status["available"] = any(channel_status.values())
    return channel_status


class NotificationService:
    """In-process notification dispatcher."""

    async def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """Fire a desktop notification. Returns True if delivered."""
        try:
            return await anotify(title, message, **kwargs)
        except Exception as exc:
            logger.warning("notification_send_failed", error=str(exc))
            return False

    async def _load_notifications(self, user_id: str) -> dict[str, Any]:
        """Load the user's persisted notification settings."""
        async with async_session() as db:
            row = (
                await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            ).scalar_one_or_none()
            if row is None:
                return {}
            return dict(row.notifications or {})

    async def _send_webhook(self, url: str, title: str, message: str, event_kind: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_DELIVERY_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json={"title": title, "message": message, "event": event_kind},
                )
                resp.raise_for_status()
        except Exception as exc:
            logger.warning("notification_webhook_failed", event=event_kind, error=str(exc))
            return False
        return True

    async def _send_email(self, to: str, subject: str, body: str) -> bool:
        """Best-effort SMTP delivery. Returns False when SMTP is unconfigured."""
        if not SMTP_CONFIGURED:
            return False
        host = os.getenv("SMTP_HOST", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")

        def _send_blocking() -> None:
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = to
            msg.set_content(body)
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)

        try:
            await asyncio.to_thread(_send_blocking)
        except Exception as exc:
            logger.warning("notification_email_failed", error=str(exc))
            return False
        return True

    async def send_user_event(
        self, user_id: str, title: str, message: str, event_kind: str
    ) -> dict[str, bool]:
        """Deliver to every channel the user enabled for ``event_kind``.

        ``event_kind`` is one of ``task_done`` / ``task_failed``; the stored
        boolean flags ``<channel>_task_done`` / ``<channel>_task_failed`` gate
        the per-channel dispatch. Desktop delivery is always attempted.
        """
        notifications = await self._load_notifications(user_id)
        results: dict[str, bool] = {"desktop": await self.send(title, message)}
        if notifications.get(f"webhook_{event_kind}"):
            url = str(notifications.get("webhook_url") or "")
            if url:
                with contextlib.suppress(Exception):
                    url = decrypt_api_key(url)
                results["webhook"] = await self._send_webhook(url, title, message, event_kind)
        if notifications.get(f"email_{event_kind}"):
            address = str(notifications.get("email_address") or "")
            if address:
                results["email"] = await self._send_email(address, title, message)
        return results

    async def task_complete(self, task_name: str, result: str | None = None) -> None:
        await self.send(
            "Task complete",
            f"{task_name} finished" + (f": {result}" if result else ""),
        )

    async def task_failed(self, task_name: str, error: str) -> None:
        await self.send("Task failed", f"{task_name}: {error}", urgency="critical")

    async def agent_message(self, agent_name: str, message: str) -> None:
        await self.send(f"{agent_name}", message)


notification_service = NotificationService()
