"""BrowserPool lifecycle tests against real Chromium instances."""

import asyncio

import pytest

from app.tools.browser_pool import BrowserPool, reset_browser_pool

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset():
    reset_browser_pool()
    yield
    reset_browser_pool()


async def test_same_session_id_reuses_instance():
    pool = BrowserPool(max_instances=2)
    try:
        a = await pool.acquire("s1")
        b = await pool.acquire("s1")
        assert a is b, "same session_id must not spawn a second browser"
        assert pool.stats()["active_sessions"] == 1
        assert b.use_count >= 1
    finally:
        await pool.close_all()


async def test_sessions_are_isolated():
    pool = BrowserPool(max_instances=2)
    try:
        a = await pool.acquire("s1")
        b = await pool.acquire("s2")
        assert a.context is not b.context, "sessions must have separate contexts"
        assert pool.stats()["active_sessions"] == 2
    finally:
        await pool.close_all()


async def test_cap_evicts_lru_instead_of_growing():
    """This is the leak fix: a third session must not mean a third Chromium."""
    pool = BrowserPool(max_instances=2)
    try:
        await pool.acquire("s1")
        await asyncio.sleep(0.01)
        await pool.acquire("s2")
        await asyncio.sleep(0.01)
        await pool.acquire("s1")  # s1 now more recent than s2
        await asyncio.sleep(0.01)

        await pool.acquire("s3")

        stats = pool.stats()
        assert stats["active_sessions"] == 2, "pool must never exceed max_instances"
        assert stats["evictions"] == 1
        live = {s["session_id"] for s in stats["sessions"]}
        assert live == {"s1", "s3"}, f"LRU (s2) should have been evicted, got {live}"
    finally:
        await pool.close_all()


async def test_idle_sessions_are_reclaimed():
    pool = BrowserPool(max_instances=2, idle_timeout=0.05)
    try:
        await pool.acquire("s1")
        assert pool.stats()["active_sessions"] == 1

        await asyncio.sleep(0.12)
        reclaimed = await pool.reclaim_idle()

        assert reclaimed == 1
        assert pool.stats()["active_sessions"] == 0, "idle session must be closed"
        assert pool.stats()["reclaimed"] == 1
    finally:
        await pool.close_all()


async def test_active_session_is_not_reclaimed():
    pool = BrowserPool(max_instances=2, idle_timeout=5.0)
    try:
        await pool.acquire("s1")
        assert await pool.reclaim_idle() == 0
        assert pool.stats()["active_sessions"] == 1
    finally:
        await pool.close_all()


async def test_release_closes_and_allows_relaunch():
    pool = BrowserPool(max_instances=2)
    try:
        first = await pool.acquire("s1")
        await pool.release("s1")
        assert pool.stats()["active_sessions"] == 0

        second = await pool.acquire("s1")
        assert second is not first, "released session must be a fresh instance"
        assert pool.stats()["active_sessions"] == 1
    finally:
        await pool.close_all()


async def test_close_all_drains_pool():
    pool = BrowserPool(max_instances=2)
    await pool.acquire("s1")
    await pool.acquire("s2")
    await pool.close_all()
    assert pool.stats()["active_sessions"] == 0


async def test_navigate_tool_works_end_to_end(tmp_path):
    """Guards the previous failure mode: 'No module named playwright'."""
    from app.tools.browser_tools import browser_extract_text, browser_navigate, close_all_sessions

    page = tmp_path / "page.html"
    page.write_text("<html><head><title>Climber</title></head><body><h1>Local Agent</h1></body></html>")
    url = page.as_uri()

    try:
        result = await browser_navigate(url=url, session_id="e2e")
        assert "Error navigating" not in result, result
        assert "Climber" in result
        assert "Local Agent" in result

        text = await browser_extract_text(selector="h1", session_id="e2e")
        assert text.strip() == "Local Agent"
    finally:
        await close_all_sessions()
