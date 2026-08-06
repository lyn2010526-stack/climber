"""Watchdog that keeps background tasks alive.

A bare `asyncio.create_task` that raises is gone forever and nothing notices.
The scheduler dying silently is exactly the failure mode that breaks 24h
unattended runs. This supervisor keeps a reference to every managed task,
detects death, and restarts with exponential backoff.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.core.logging_setup import write_crash_dump

logger = structlog.get_logger()

INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0
BACKOFF_FACTOR = 2.0


@dataclass
class SupervisedTask:
    """Bookkeeping for one supervised background task."""

    name: str
    factory: Callable[[], Awaitable[Any]]
    task: asyncio.Task | None = None
    restarts: int = 0
    failures: int = 0
    last_error: str | None = None
    last_started: float = field(default_factory=time.time)
    backoff: float = INITIAL_BACKOFF
    stopped: bool = False
    crashed: bool = False

    @property
    def alive(self) -> bool:
        return self.task is not None and not self.task.done()

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "alive": self.alive,
            "restarts": self.restarts,
            "failures": self.failures,
            "last_error": self.last_error,
            "uptime_seconds": round(time.time() - self.last_started, 1),
            "stopped": self.stopped,
        }


class Watchdog:
    """Supervises long-lived background coroutines with auto-restart."""

    def __init__(self, check_interval: float = 10.0) -> None:
        self.check_interval = check_interval
        self._tasks: dict[str, SupervisedTask] = {}
        self._monitor: asyncio.Task | None = None
        self._running = False

    def register(self, name: str, factory: Callable[[], Awaitable[Any]]) -> SupervisedTask:
        """Register a coroutine factory to be kept alive."""
        supervised = SupervisedTask(name=name, factory=factory)
        self._tasks[name] = supervised
        return supervised

    async def start(self) -> None:
        """Launch all registered tasks and the monitor loop."""
        if self._running:
            return
        self._running = True
        for supervised in self._tasks.values():
            self._spawn(supervised)
        self._monitor = asyncio.create_task(self._monitor_loop(), name="watchdog-monitor")
        logger.info("watchdog_started", tasks=list(self._tasks))

    def _spawn(self, supervised: SupervisedTask) -> None:
        supervised.task = asyncio.create_task(
            self._guarded(supervised), name=f"supervised:{supervised.name}"
        )
        supervised.last_started = time.time()

    async def _guarded(self, supervised: SupervisedTask) -> None:
        """Run the coroutine, recording any exception instead of losing it.

        The exception is deliberately not re-raised: an unretrieved task
        exception produces asyncio noise and gives us nothing the crash
        record does not already capture.
        """
        try:
            supervised.crashed = False
            await supervised.factory()
            logger.info("supervised_task_completed", name=supervised.name)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            supervised.crashed = True
            supervised.failures += 1
            supervised.last_error = f"{type(exc).__name__}: {exc}"
            dump = write_crash_dump(exc, {"task": supervised.name})
            logger.error(
                "supervised_task_crashed",
                name=supervised.name,
                error=supervised.last_error,
                crash_dump=str(dump) if dump else None,
                exc_info=True,
            )

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - monitor must never die
                logger.error("watchdog_monitor_error", error=str(exc), exc_info=True)

    async def _check_once(self) -> None:
        for supervised in self._tasks.values():
            if supervised.stopped or supervised.alive:
                continue

            # Task is dead. Only resurrect it if it died from an exception;
            # a coroutine that returned normally is considered finished.
            if not supervised.crashed:
                supervised.stopped = True
                continue

            await asyncio.sleep(supervised.backoff)
            supervised.restarts += 1
            supervised.backoff = min(supervised.backoff * BACKOFF_FACTOR, MAX_BACKOFF)
            logger.warning(
                "supervised_task_restarting",
                name=supervised.name,
                restarts=supervised.restarts,
                backoff=supervised.backoff,
            )
            self._spawn(supervised)

    async def check_now(self) -> None:
        """Force one supervision pass (used by tests and the health endpoint)."""
        await self._check_once()

    async def stop(self) -> None:
        """Cancel the monitor and all supervised tasks."""
        self._running = False
        if self._monitor is not None and not self._monitor.done():
            self._monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._monitor
        self._monitor = None

        for supervised in self._tasks.values():
            supervised.stopped = True
            if supervised.task is not None and not supervised.task.done():
                supervised.task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await supervised.task
        logger.info("watchdog_stopped")

    def health(self) -> dict[str, Any]:
        tasks = [t.snapshot() for t in self._tasks.values()]
        expected = [t for t in tasks if not t["stopped"]]
        return {
            "running": self._running,
            "healthy": all(t["alive"] for t in expected),
            "total_tasks": len(tasks),
            "alive_tasks": sum(1 for t in tasks if t["alive"]),
            "total_restarts": sum(t["restarts"] for t in tasks),
            "tasks": tasks,
        }


_watchdog: Watchdog | None = None


def get_watchdog() -> Watchdog:
    global _watchdog
    if _watchdog is None:
        _watchdog = Watchdog()
    return _watchdog


def reset_watchdog() -> None:
    global _watchdog
    _watchdog = None
