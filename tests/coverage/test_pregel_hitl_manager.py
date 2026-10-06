"""Coverage tests for app.core.engine.pregel.hitl."""

from __future__ import annotations

import asyncio

import pytest

from app.core.engine.pregel.hitl import HITLManager, Interrupt


def test_interrupt_model_defaults() -> None:
    intr = Interrupt(node="n")
    assert intr.id.startswith("intr-")
    assert intr.status == "pending"
    assert intr.thread_id == "default"
    assert intr.metadata == {}


async def test_interrupt_resume_wait_for_roundtrip() -> None:
    mgr = HITLManager()
    iid = await mgr.interrupt("node-a", value={"q": 1}, thread_id="t1", checkpoint_id="cp1")
    intr = await mgr.get(iid)
    assert intr is not None
    assert intr.checkpoint_id == "cp1"

    async def resolver() -> None:
        await asyncio.sleep(0)
        await mgr.resume(iid, "answer")

    await asyncio.gather(resolver(), mgr.wait_for(iid, timeout=1.0))
    assert await mgr.wait_for(iid) == "answer"
    assert mgr.pending_count == 0


async def test_interrupt_requires_existing_event() -> None:
    mgr = HITLManager()
    with pytest.raises(KeyError):
        await mgr.resume("missing", 1)
    with pytest.raises(KeyError):
        await mgr.cancel("missing")
    with pytest.raises(KeyError):
        await mgr.wait_for("missing")


async def test_resume_twice_raises() -> None:
    mgr = HITLManager()
    iid = await mgr.interrupt("n")
    await mgr.resume(iid, "x")
    with pytest.raises(RuntimeError):
        await mgr.resume(iid, "y")


async def test_cancel_sets_status_and_wakes_waiter() -> None:
    mgr = HITLManager()
    iid = await mgr.interrupt("n")

    async def canceller() -> None:
        await asyncio.sleep(0)
        await mgr.cancel(iid)

    with pytest.raises(RuntimeError):
        await asyncio.gather(canceller(), mgr.wait_for(iid, timeout=1.0))
    intr = await mgr.get(iid)
    assert intr is not None and intr.status == "cancelled"


async def test_wait_for_timeout() -> None:
    mgr = HITLManager()
    iid = await mgr.interrupt("n")
    with pytest.raises(TimeoutError):
        await mgr.wait_for(iid, timeout=0.01)


async def test_get_pending_filters_by_thread() -> None:
    mgr = HITLManager()
    a = await mgr.interrupt("a", thread_id="ta")
    b = await mgr.interrupt("b", thread_id="tb")
    all_pending = await mgr.get_pending()
    assert {i.id for i in all_pending} == {a, b}

    only_a = await mgr.get_pending("ta")
    assert [i.id for i in only_a] == [a]

    await mgr.resume(a, 1)
    assert [i.id for i in await mgr.get_pending()] == [b]
    assert await mgr.get_pending("missing") == []
    assert await mgr.get("missing") is None


async def test_auto_expire_with_default_timeout() -> None:
    mgr = HITLManager(default_timeout=0.01)
    iid = await mgr.interrupt("n")
    await asyncio.sleep(0.05)
    intr = await mgr.get(iid)
    assert intr is not None and intr.status == "expired"
    assert intr.resolved_at is not None
    assert mgr.pending_count == 0


async def test_resume_and_cancel_without_event() -> None:
    mgr = HITLManager()
    a = await mgr.interrupt("a")
    mgr._pending_events.pop(a)
    resolved = await mgr.resume(a, "v")
    assert resolved.status == "resolved"

    b = await mgr.interrupt("b")
    mgr._pending_events.pop(b)
    cancelled = await mgr.cancel(b)
    assert cancelled.status == "cancelled"


async def test_auto_expire_when_event_missing() -> None:
    mgr = HITLManager(default_timeout=0.01)
    iid = await mgr.interrupt("n")
    mgr._pending_events.pop(iid)
    await asyncio.sleep(0.05)
    intr = await mgr.get(iid)
    assert intr is not None and intr.status == "expired"


async def test_auto_expire_ignores_already_resolved() -> None:
    mgr = HITLManager(default_timeout=0.01)
    iid = await mgr.interrupt("n")
    await mgr.resume(iid, "ok")
    await asyncio.sleep(0.05)
    intr = await mgr.get(iid)
    assert intr is not None and intr.status == "resolved"
