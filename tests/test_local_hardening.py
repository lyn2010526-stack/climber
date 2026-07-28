"""Local-first hardening: SQLite WAL/concurrency and memory guardian."""

import asyncio

import pytest
from sqlalchemy import text

from app.core.memory_guardian import MemoryGuardian, reset_memory_guardian
from app.storage import async_session, db_health, engine, init_db

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset():
    reset_memory_guardian()
    yield
    reset_memory_guardian()


# ── SQLite hardening ───────────────────────────────────────────────────────


async def test_wal_mode_is_enabled():
    """Default rollback journal serialises writers; WAL is what fixes it."""
    health = await db_health()
    assert health["connected"] is True
    if health["backend"] == "sqlite":
        assert str(health["journal_mode"]).lower() == "wal", health


async def test_busy_timeout_is_set():
    health = await db_health()
    if health["backend"] == "sqlite":
        assert health["busy_timeout_ms"] >= 1000, "a zero busy timeout fails instantly under contention"


async def test_foreign_keys_enforced():
    async with engine.connect() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        assert result.scalar() == 1


async def test_concurrent_writes_do_not_lock_up():
    """The 'database is locked' regression guard."""
    await init_db()
    from app.storage.models_platform import Workflow

    async def writer(index: int) -> str:
        async with async_session() as db:
            wf = Workflow(name=f"concurrent-{index}", nodes=[], edges=[])
            db.add(wf)
            await db.commit()
            return wf.id

    ids = await asyncio.gather(*(writer(i) for i in range(12)))
    assert len(set(ids)) == 12, "every concurrent write should have committed"

    async with async_session() as db:
        rows = (await db.execute(text("SELECT COUNT(*) FROM workflows WHERE name LIKE 'concurrent-%'"))).scalar()
        assert rows >= 12


async def test_platform_models_are_registered():
    """models_platform was missing from init_db's import list."""
    await init_db()
    from app.storage import Base

    for table in ("workflows", "crews", "skills", "traces", "cluster_nodes", "document_chunks"):
        assert table in Base.metadata.tables, f"{table} not registered"


# ── Memory guardian ────────────────────────────────────────────────────────


async def test_guardian_reads_real_rss():
    guardian = MemoryGuardian(limit_mb=4096)
    sample = guardian.sample()
    assert sample.rss_mb > 0, "should read actual process memory"
    assert guardian.stats()["current_mb"] > 0


async def test_below_threshold_takes_no_action():
    guardian = MemoryGuardian(limit_mb=1_000_000)  # never reachable
    result = await guardian.check()
    assert result["action"] == "none"
    assert guardian.stats()["gc_runs"] == 0


async def test_soft_threshold_triggers_gc():
    guardian = MemoryGuardian(limit_mb=1)  # current RSS far exceeds this
    guardian.hard_ratio = 10_000  # keep us in the soft band
    result = await guardian.check()
    assert result["action"] == "gc"
    assert guardian.stats()["gc_runs"] == 1


async def test_hard_threshold_invokes_relief_callbacks():
    guardian = MemoryGuardian(limit_mb=1)
    fired = []

    async def relief():
        fired.append(True)

    guardian.register_relief(relief)
    result = await guardian.check()

    assert result["action"] == "relief"
    assert fired == [True], "relief callback must run under memory pressure"
    assert guardian.stats()["relief_runs"] == 1


async def test_failing_relief_callback_does_not_break_guardian():
    guardian = MemoryGuardian(limit_mb=1)

    async def bad():
        raise RuntimeError("relief exploded")

    ok = []

    async def good():
        ok.append(True)

    guardian.register_relief(bad)
    guardian.register_relief(good)

    result = await guardian.check()
    assert result["action"] == "relief"
    assert ok == [True], "one bad callback must not block the others"


async def test_guardian_start_stop_lifecycle():
    guardian = MemoryGuardian(limit_mb=100_000, check_interval=0.01)
    await guardian.start()
    assert guardian.stats()["running"] is True
    await asyncio.sleep(0.05)
    await guardian.stop()
    assert guardian.stats()["running"] is False


async def test_history_is_bounded():
    guardian = MemoryGuardian(limit_mb=1_000_000)
    for _ in range(200):
        guardian.sample()
    assert guardian.stats()["samples"] <= 120, "history must not grow without bound"
