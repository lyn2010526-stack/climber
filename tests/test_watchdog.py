"""Watchdog supervision tests: crash detection and auto-restart."""

import asyncio

import pytest

from app.core.watchdog import Watchdog, reset_watchdog

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset():
    reset_watchdog()
    yield
    reset_watchdog()


async def test_healthy_task_stays_alive():
    async def forever():
        while True:
            await asyncio.sleep(0.01)

    wd = Watchdog(check_interval=0.02)
    wd.register("forever", forever)
    try:
        await wd.start()
        await asyncio.sleep(0.1)
        health = wd.health()
        assert health["healthy"] is True
        assert health["alive_tasks"] == 1
        assert health["total_restarts"] == 0
    finally:
        await wd.stop()


async def test_crashed_task_is_restarted():
    """The core fix: a task that raises must come back, not vanish."""
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise RuntimeError(f"boom {attempts}")
        while True:
            await asyncio.sleep(0.01)

    wd = Watchdog(check_interval=0.02)
    task = wd.register("flaky", flaky)
    task.backoff = 0.01  # keep the test fast
    try:
        await wd.start()
        for _ in range(60):
            await asyncio.sleep(0.02)
            if attempts >= 3 and task.alive:
                break

        assert attempts >= 3, f"task should have been restarted, ran {attempts}x"
        assert task.restarts >= 2
        assert task.failures >= 2
        assert "boom" in (task.last_error or "")
        assert wd.health()["healthy"] is True, "should recover to healthy"
    finally:
        await wd.stop()


async def test_crash_is_recorded_not_swallowed():
    async def dies():
        raise ValueError("recorded failure")

    wd = Watchdog(check_interval=0.02)
    task = wd.register("dies", dies)
    task.backoff = 0.01
    try:
        await wd.start()
        await asyncio.sleep(0.08)
        assert task.failures >= 1
        assert "ValueError" in (task.last_error or "")
        assert "recorded failure" in (task.last_error or "")
    finally:
        await wd.stop()


async def test_cleanly_finished_task_is_not_resurrected():
    runs = 0

    async def once():
        nonlocal runs
        runs += 1

    wd = Watchdog(check_interval=0.02)
    wd.register("once", once)
    try:
        await wd.start()
        await asyncio.sleep(0.12)
        assert runs == 1, "a task that returns normally must not be restarted"
    finally:
        await wd.stop()


async def test_stop_cancels_everything():
    async def forever():
        while True:
            await asyncio.sleep(0.01)

    wd = Watchdog(check_interval=0.02)
    task = wd.register("forever", forever)
    await wd.start()
    await asyncio.sleep(0.05)
    await wd.stop()

    assert wd.health()["running"] is False
    assert task.alive is False


async def test_backoff_grows_on_repeated_failure():
    async def always_dies():
        raise RuntimeError("nope")

    wd = Watchdog(check_interval=0.01)
    task = wd.register("always_dies", always_dies)
    task.backoff = 0.01
    try:
        await wd.start()
        await asyncio.sleep(0.15)
        assert task.backoff > 0.01, "backoff must grow to avoid hot restart loops"
        assert task.restarts >= 1
    finally:
        await wd.stop()
