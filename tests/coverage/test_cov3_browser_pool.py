"""Coverage tests for app.tools.browser_pool (fake browser sessions)."""

from __future__ import annotations

import asyncio
import sys
import types

import pytest

from app.tools import browser_pool
from app.tools.browser_pool import BrowserPool, BrowserSession


class FakeComponent:
    """Fake playwright/browser/context supporting close() and stop()."""

    def __init__(self, exc=None):
        self.exc = exc
        self.close_count = 0
        self.stop_count = 0

    async def close(self):
        self.close_count += 1
        if self.exc:
            raise self.exc

    async def stop(self):
        self.stop_count += 1
        if self.exc:
            raise self.exc


def make_session(session_id: str) -> BrowserSession:
    return BrowserSession(
        session_id=session_id,
        playwright=FakeComponent(),
        browser=FakeComponent(),
        context=FakeComponent(),
    )


def install_launch(monkeypatch, pool: BrowserPool):
    created = []

    async def _fake_launch(session_id):
        s = make_session(session_id)
        created.append(s)
        return s

    monkeypatch.setattr(pool, "_launch", _fake_launch)
    return created


# ─── BrowserSession ─────────────────────────────────────────────────────────


def test_session_touch_and_idle():
    s = make_session("a")
    assert s.use_count == 0
    assert s.idle_seconds >= 0
    s.touch()
    assert s.use_count == 1


async def test_session_close_calls_all_closers():
    s = make_session("a")
    await s.close()
    assert s.context.close_count == 1
    assert s.browser.close_count == 1
    assert s.playwright.stop_count == 1


async def test_session_close_swallows_errors():
    s = BrowserSession(
        session_id="a",
        playwright=FakeComponent(exc=RuntimeError("p")),
        browser=FakeComponent(exc=RuntimeError("b")),
        context=FakeComponent(exc=RuntimeError("c")),
    )
    await s.close()  # must not raise
    assert s.context.close_count == 1
    assert s.browser.close_count == 1
    assert s.playwright.stop_count == 1


# ─── acquire / eviction ─────────────────────────────────────────────────────


async def test_acquire_creates_and_reuses(monkeypatch):
    pool = BrowserPool(max_instances=2, sweep_interval=1000)
    created = install_launch(monkeypatch, pool)

    first = await pool.acquire("a")
    assert pool._sessions["a"] is first
    assert len(created) == 1

    again = await pool.acquire("a")
    assert again is first
    assert again.use_count == 1
    assert len(created) == 1
    await pool.close_all()


async def test_acquire_evicts_lru_at_capacity(monkeypatch):
    pool = BrowserPool(max_instances=2, sweep_interval=1000)
    install_launch(monkeypatch, pool)

    a = await pool.acquire("a")
    b = await pool.acquire("b")
    a.last_used = 100.0
    b.last_used = 200.0

    c = await pool.acquire("c")
    assert set(pool._sessions) == {"b", "c"}
    assert pool._evictions == 1
    assert a.context.close_count == 1  # victim closed
    assert c.session_id == "c"
    await pool.close_all()


async def test_evict_lru_on_empty_pool_is_noop():
    pool = BrowserPool()
    await pool._evict_lru_locked()
    assert pool._evictions == 0


async def test_release_existing_and_missing(monkeypatch):
    pool = BrowserPool(sweep_interval=1000)
    install_launch(monkeypatch, pool)
    s = await pool.acquire("a")
    await pool.release("a")
    assert "a" not in pool._sessions
    assert s.context.close_count == 1
    # releasing an unknown session is a no-op
    await pool.release("missing")
    await pool.close_all()


# ─── close_all / sweeper ────────────────────────────────────────────────────


async def test_close_all_closes_and_stops_sweeper(monkeypatch):
    pool = BrowserPool(sweep_interval=1000)
    install_launch(monkeypatch, pool)
    s = await pool.acquire("a")
    assert pool._sweeper is not None
    await pool.close_all()
    assert pool._sessions == {}
    assert s.context.close_count == 1
    assert pool._sweeper is None


async def test_close_all_handles_close_timeout(monkeypatch):
    pool = BrowserPool(sweep_interval=1000)

    async def _fake_launch(session_id):
        s = make_session(session_id)

        async def _hang():
            await asyncio.Event().wait()  # never resolves

        async def _close():
            await _hang()

        s.context.close = _close  # type: ignore[method-assign]
        return s

    monkeypatch.setattr(pool, "_launch", _fake_launch)
    monkeypatch.setattr(browser_pool, "SESSION_CLOSE_TIMEOUT", 0.01)
    await pool.acquire("a")
    await pool.close_all()
    assert pool._sessions == {}


async def test_launch_builds_session_from_playwright(monkeypatch):
    context_obj = object()
    browser_calls = {}

    class FakeBrowser:
        async def new_context(self, **kwargs):
            browser_calls["new_context"] = kwargs
            return context_obj

    class FakeChromium:
        async def launch(self, **kwargs):
            browser_calls["launch"] = kwargs
            return FakeBrowser()

    class FakePlaywright:
        def __init__(self):
            self.chromium = FakeChromium()

        async def stop(self):
            return None

    playwright_obj = FakePlaywright()

    class FakeAsyncPlaywrightCtx:
        async def start(self):
            return playwright_obj

    async_api = types.ModuleType("playwright.async_api")
    async_api.async_playwright = lambda: FakeAsyncPlaywrightCtx()
    pkg = types.ModuleType("playwright")
    pkg.async_api = async_api
    monkeypatch.setitem(sys.modules, "playwright", pkg)
    monkeypatch.setitem(sys.modules, "playwright.async_api", async_api)

    pool = BrowserPool(sweep_interval=1000)
    session = await pool._launch("s1")
    assert session.session_id == "s1"
    assert session.playwright is playwright_obj
    assert session.context is context_obj
    assert browser_calls["launch"]["headless"] is True
    assert "--no-sandbox" in browser_calls["launch"]["args"]
    assert browser_calls["new_context"]["viewport"] == {"width": 1280, "height": 720}


async def test_close_all_no_sweeper_manual_sessions():
    pool = BrowserPool(sweep_interval=1000)
    a = make_session("a")
    b = make_session("b")
    pool._sessions = {"a": a, "b": b}
    await pool.close_all()
    assert a.context.close_count == 1
    assert b.context.close_count == 1
    assert pool._sessions == {}


async def test_close_all_empty_pool():
    pool = BrowserPool(sweep_interval=1000)
    await pool.close_all()
    assert pool._sessions == {}


def test_ensure_sweeper_without_running_loop():
    pool = BrowserPool(sweep_interval=1000)
    pool._ensure_sweeper()  # RuntimeError path -> no task, no raise
    assert pool._sweeper is None


async def test_ensure_sweeper_recreates_when_done(monkeypatch):
    pool = BrowserPool(sweep_interval=1000)
    pool._ensure_sweeper()
    first = pool._sweeper
    assert first is not None
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    pool._ensure_sweeper()
    assert pool._sweeper is not None
    assert pool._sweeper is not first
    await pool._stop_sweeper()


async def test_stop_sweeper_when_none():
    pool = BrowserPool()
    await pool._stop_sweeper()
    assert pool._sweeper is None


async def test_sweep_loop_reclaims(monkeypatch):
    pool = BrowserPool(sweep_interval=0)
    calls = []

    async def _fake_reclaim():
        calls.append(1)
        return 0

    monkeypatch.setattr(pool, "reclaim_idle", _fake_reclaim)
    task = asyncio.create_task(pool._sweep_loop())
    for _ in range(5):
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls  # loop ran at least one reclaim cycle


# ─── reclaim_idle / stats ───────────────────────────────────────────────────


async def test_reclaim_idle_only_stale(monkeypatch):
    pool = BrowserPool(idle_timeout=100.0, sweep_interval=1000)
    install_launch(monkeypatch, pool)
    stale = await pool.acquire("stale")
    fresh = await pool.acquire("fresh")
    stale.last_used = 0.0  # far in the past
    fresh.touch()

    count = await pool.reclaim_idle()
    assert count == 1
    assert pool._reclaimed == 1
    assert set(pool._sessions) == {"fresh"}
    assert stale.context.close_count == 1
    await pool.close_all()


async def test_stats_reports_sessions(monkeypatch):
    pool = BrowserPool(max_instances=3, idle_timeout=10.0, sweep_interval=1000)
    install_launch(monkeypatch, pool)
    await pool.acquire("a")
    stats = pool.stats()
    assert stats["active_sessions"] == 1
    assert stats["max_instances"] == 3
    assert stats["idle_timeout"] == 10.0
    assert stats["evictions"] == 0
    assert stats["reclaimed"] == 0
    assert stats["sessions"][0]["session_id"] == "a"
    assert stats["sessions"][0]["use_count"] == 0
    await pool.close_all()


def test_get_browser_pool_singleton(monkeypatch):
    monkeypatch.setattr(browser_pool, "_pool", None)
    p1 = browser_pool.get_browser_pool()
    p2 = browser_pool.get_browser_pool()
    assert p1 is p2
    assert isinstance(p1, BrowserPool)
    monkeypatch.setattr(browser_pool, "_pool", None)
