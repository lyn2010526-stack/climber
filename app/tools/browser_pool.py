"""Browser instance pool with lifecycle management.

Keeps a bounded number of Playwright browser instances alive, evicts the
least-recently-used one when the cap is reached, and reclaims instances that
have been idle for too long. This is what makes 24h unattended operation
possible: without it every session leaks a Chromium process.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()

DEFAULT_MAX_INSTANCES = 2
DEFAULT_IDLE_TIMEOUT = 300.0  # 5 minutes
DEFAULT_SWEEP_INTERVAL = 60.0


@dataclass
class BrowserSession:
    """A single isolated browser session."""

    session_id: str
    playwright: Any
    browser: Any
    context: Any
    created_at: float = field(default_factory=time.monotonic)
    last_used: float = field(default_factory=time.monotonic)
    use_count: int = 0

    def touch(self) -> None:
        self.last_used = time.monotonic()
        self.use_count += 1

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_used

    async def close(self) -> None:
        closers: list[Callable[[], Awaitable[Any]]] = [
            lambda: self.context.close(),
            lambda: self.browser.close(),
            lambda: self.playwright.stop(),
        ]
        for closer in closers:
            try:
                await closer()
            except Exception as exc:  # pragma: no cover - best effort teardown
                logger.debug("browser_session_close_error", session_id=self.session_id, error=str(exc))


class BrowserPool:
    """Bounded pool of browser sessions with idle reclamation."""

    def __init__(
        self,
        max_instances: int = DEFAULT_MAX_INSTANCES,
        idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
        sweep_interval: float = DEFAULT_SWEEP_INTERVAL,
    ) -> None:
        self.max_instances = max_instances
        self.idle_timeout = idle_timeout
        self.sweep_interval = sweep_interval
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        self._sweeper: asyncio.Task[Any] | None = None
        self._evictions = 0
        self._reclaimed = 0

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def acquire(self, session_id: str) -> BrowserSession:
        """Get an existing session or create one, evicting LRU if at capacity."""
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None:
                existing.touch()
                return existing

            if len(self._sessions) >= self.max_instances:
                await self._evict_lru_locked()

            session = await self._launch(session_id)
            self._sessions[session_id] = session
            self._ensure_sweeper()
            logger.info(
                "browser_session_created",
                session_id=session_id,
                pool_size=len(self._sessions),
            )
            return session

    async def _launch(self, session_id: str) -> BrowserSession:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="AgentEngine/0.1 (compatible; Auto)",
        )
        return BrowserSession(
            session_id=session_id,
            playwright=playwright,
            browser=browser,
            context=context,
        )

    async def _evict_lru_locked(self) -> None:
        if not self._sessions:
            return
        victim_id = min(self._sessions, key=lambda k: self._sessions[k].last_used)
        victim = self._sessions.pop(victim_id)
        self._evictions += 1
        logger.info("browser_session_evicted", session_id=victim_id, idle=round(victim.idle_seconds, 1))
        await victim.close()

    async def release(self, session_id: str) -> None:
        """Explicitly close one session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            await session.close()
            logger.info("browser_session_closed", session_id=session_id)

    async def close_all(self) -> None:
        """Tear the whole pool down (called on app shutdown)."""
        await self._stop_sweeper()
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await session.close()
        if sessions:
            logger.info("browser_pool_drained", count=len(sessions))

    # ── idle reclamation ───────────────────────────────────────────────────

    def _ensure_sweeper(self) -> None:
        if self._sweeper is None or self._sweeper.done():
            try:
                self._sweeper = asyncio.create_task(self._sweep_loop())
            except RuntimeError:  # no running loop (sync context)
                self._sweeper = None

    async def _sweep_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.sweep_interval)
                await self.reclaim_idle()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - sweeper must never die
                logger.warning("browser_sweep_error", error=str(exc))

    async def reclaim_idle(self) -> int:
        """Close sessions idle beyond the timeout. Returns count reclaimed."""
        async with self._lock:
            stale = [
                sid for sid, s in self._sessions.items() if s.idle_seconds > self.idle_timeout
            ]
            victims = [self._sessions.pop(sid) for sid in stale]
        for victim in victims:
            await victim.close()
            self._reclaimed += 1
            logger.info("browser_session_reclaimed", session_id=victim.session_id)
        return len(victims)

    async def _stop_sweeper(self) -> None:
        if self._sweeper is not None and not self._sweeper.done():
            self._sweeper.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._sweeper
        self._sweeper = None

    # ── introspection ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        return {
            "active_sessions": len(self._sessions),
            "max_instances": self.max_instances,
            "idle_timeout": self.idle_timeout,
            "evictions": self._evictions,
            "reclaimed": self._reclaimed,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "idle_seconds": round(s.idle_seconds, 1),
                    "use_count": s.use_count,
                    "age_seconds": round(time.monotonic() - s.created_at, 1),
                }
                for s in self._sessions.values()
            ],
        }


_pool: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    """Global pool accessor."""
    global _pool
    if _pool is None:
        _pool = BrowserPool()
    return _pool


def reset_browser_pool() -> None:
    """Test helper: drop the global pool without closing it."""
    global _pool
    _pool = None
