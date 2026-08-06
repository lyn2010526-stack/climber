"""Memory guardian for long-running unattended operation.

Without this, a multi-day session grows until the OS kills the process. The
guardian samples RSS, triggers GC at the soft threshold, and invokes registered
pressure-relief callbacks (context compaction, cache eviction) at the hard one.
"""

from __future__ import annotations

import asyncio
import contextlib
import gc
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()

SOFT_RATIO = 0.75
HARD_RATIO = 0.90


@dataclass
class MemorySample:
    timestamp: float
    rss_mb: float
    percent_of_limit: float


@dataclass
class MemoryGuardian:
    """Samples process memory and applies relief when it climbs."""

    limit_mb: int = 2048
    check_interval: float = 60.0
    soft_ratio: float = SOFT_RATIO
    hard_ratio: float = HARD_RATIO

    _relief_callbacks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
    _history: list[MemorySample] = field(default_factory=list)
    _task: asyncio.Task | None = None
    _gc_runs: int = 0
    _relief_runs: int = 0
    _peak_mb: float = 0.0

    def register_relief(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Add a coroutine invoked when memory crosses the hard threshold."""
        self._relief_callbacks.append(callback)

    # ── sampling ───────────────────────────────────────────────────────────

    def current_rss_mb(self) -> float:
        """Resident set size in MB, falling back gracefully if psutil is absent."""
        try:
            import psutil

            return psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            try:
                import resource

                usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                # Linux reports KB, macOS reports bytes
                return usage / 1024
            except Exception:
                return 0.0

    def sample(self) -> MemorySample:
        rss = self.current_rss_mb()
        self._peak_mb = max(self._peak_mb, rss)
        entry = MemorySample(
            timestamp=time.time(),
            rss_mb=round(rss, 1),
            percent_of_limit=round(rss / self.limit_mb * 100, 1) if self.limit_mb else 0.0,
        )
        self._history.append(entry)
        if len(self._history) > 120:
            self._history = self._history[-120:]
        return entry

    # ── enforcement ────────────────────────────────────────────────────────

    async def check(self) -> dict[str, Any]:
        """Sample once and act on the result."""
        entry = self.sample()
        ratio = entry.rss_mb / self.limit_mb if self.limit_mb else 0.0
        action = "none"

        if ratio >= self.hard_ratio:
            action = "relief"
            collected = gc.collect()
            self._gc_runs += 1
            self._relief_runs += 1
            logger.warning(
                "memory_hard_threshold",
                rss_mb=entry.rss_mb,
                limit_mb=self.limit_mb,
                gc_collected=collected,
            )
            for callback in self._relief_callbacks:
                try:
                    await callback()
                except Exception as exc:
                    logger.error("memory_relief_callback_failed", error=str(exc))
        elif ratio >= self.soft_ratio:
            action = "gc"
            collected = gc.collect()
            self._gc_runs += 1
            logger.info("memory_soft_threshold", rss_mb=entry.rss_mb, gc_collected=collected)

        return {"rss_mb": entry.rss_mb, "ratio": round(ratio, 3), "action": action}

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self.check()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - guardian must not die
                logger.error("memory_guardian_error", error=str(exc))

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="memory-guardian")
            logger.info("memory_guardian_started", limit_mb=self.limit_mb)

    async def stop(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
        self._task = None

    def stats(self) -> dict[str, Any]:
        current = self._history[-1] if self._history else None
        return {
            "current_mb": current.rss_mb if current else round(self.current_rss_mb(), 1),
            "peak_mb": round(self._peak_mb, 1),
            "limit_mb": self.limit_mb,
            "soft_threshold_mb": round(self.limit_mb * self.soft_ratio, 1),
            "hard_threshold_mb": round(self.limit_mb * self.hard_ratio, 1),
            "gc_runs": self._gc_runs,
            "relief_runs": self._relief_runs,
            "samples": len(self._history),
            "running": self._task is not None and not self._task.done(),
        }


_guardian: MemoryGuardian | None = None


def get_memory_guardian() -> MemoryGuardian:
    global _guardian
    if _guardian is None:
        from app.config import settings

        _guardian = MemoryGuardian(
            limit_mb=settings.memory_limit_mb,
            check_interval=settings.memory_check_interval,
        )
    return _guardian


def reset_memory_guardian() -> None:
    global _guardian
    _guardian = None
