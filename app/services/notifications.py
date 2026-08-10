"""Notification service for Climber.

Provides a simple interface to fire desktop notifications from anywhere in
the backend. All calls are best-effort: failures are logged and swallowed.
Recent notifications are kept in an in-process ring buffer so the web UI
can list a history of dispatched notifications.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any

import structlog

from app.utils.notifications import notify

logger = structlog.get_logger()

_MAX_HISTORY = 200


class NotificationService:
    """In-process notification dispatcher with a bounded history."""

    def __init__(self) -> None:
        self._history: deque[dict[str, Any]] = deque(maxlen=_MAX_HISTORY)

    async def send(self, title: str, message: str, **kwargs: Any) -> bool:
        """Fire a desktop notification. Returns True if delivered."""
        try:
            ok = notify(title, message, **kwargs)
        except Exception as exc:
            logger.warning("notification_send_failed", error=str(exc))
            ok = False
        self._history.appendleft({
            "title": title,
            "message": message,
            "urgency": kwargs.get("urgency", "normal"),
            "delivered": ok,
            "created_at": datetime.now(UTC).isoformat(),
        })
        return ok

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recently dispatched notifications."""
        items = list(self._history)
        if limit and limit > 0:
            items = items[:limit]
        return items

    async def clear(self) -> int:
        """Clear notification history. Returns the number removed."""
        count = len(self._history)
        self._history.clear()
        return count

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
