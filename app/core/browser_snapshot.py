"""Browser page state snapshots.

"""

from __future__ import annotations

import logging
import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PageSnapshot:
    session_id: str
    url: str
    title: str
    screenshot: str | None = None
    dom_summary: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class BrowserSnapshotService:
    """Capture browser page state snapshots.

    """

    def __init__(self, max_snapshots: int = 20):
        self._snapshots: dict[str, list[PageSnapshot]] = {}
        self._max_snapshots = max_snapshots

    async def capture(self, session_id: str, page: Any) -> PageSnapshot:
        """Capture current page state."""
        try:
            url = page.url
            title = await page.title()
            screenshot_bytes = await page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
            dom_summary = await self._summarize_dom(page)
            snapshot = PageSnapshot(
                session_id=session_id,
                url=url,
                title=title,
                screenshot=screenshot_b64,
                dom_summary=dom_summary,
            )
            self._store(session_id, snapshot)
            return snapshot
        except Exception as e:
            logger.error("snapshot_capture_failed", session_id=session_id, error=str(e))
            raise

    async def _summarize_dom(self, page: Any) -> str:
        try:
            return await page.evaluate(
                """() => {
                const elements = document.querySelectorAll('h1, h2, h3, button, input, a');
                const parts = [];
                elements.forEach(el => {
                    parts.push(el.tagName + ':' + (el.innerText || el.placeholder || el.href || '').trim().slice(0, 80));
                });
                return parts.join('\\n');
                }"""
            )
        except Exception:
            return ""

    def get_history(self, session_id: str) -> list[PageSnapshot]:
        return list(self._snapshots.get(session_id, []))

    def _store(self, session_id: str, snapshot: PageSnapshot) -> None:
        if session_id not in self._snapshots:
            self._snapshots[session_id] = []
        history = self._snapshots[session_id]
        history.append(snapshot)
        if len(history) > self._max_snapshots:
            self._snapshots[session_id] = history[-self._max_snapshots:]


browser_snapshot_service = BrowserSnapshotService()
