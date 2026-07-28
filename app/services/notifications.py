"""Notification service for Climber.

Provides a simple interface to fire desktop notifications from anywhere in
the backend. All calls are best-effort: failures are logged and swallowed.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.utils.notifications import notify

logger = structlog.get_logger()


class NotificationService:
    """In-process notification dispatcher."""

    async def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """Fire a desktop notification. Returns True if delivered."""
        try:
            return notify(title, message, **kwargs)
        except Exception as exc:
            logger.warning("notification_send_failed", error=str(exc))
            return False

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
