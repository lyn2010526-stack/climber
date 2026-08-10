"""Tests for AutoLoopEngine."""

import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.auto_loop import AutoLoopEngine, AutoLoopTaskStatus
from app.storage import Base
from app.storage.models_platform import AutoLoopTask


@pytest.fixture
def engine():
    return AutoLoopEngine(heartbeat_timeout=1.0, recovery_check_interval=0.5)


@pytest.mark.asyncio
async def test_start_task(engine):
    await engine.start()
    task_id = engine.start_task("test objective", max_steps=3)
    assert task_id in engine._tasks
    # Wait for the asyncio task to start executing
    for _ in range(50):
        status = await engine.get_status(task_id)
        if status and status["status"] == AutoLoopTaskStatus.RUNNING.value:
            break
        await asyncio.sleep(0.05)
    status = await engine.get_status(task_id)
    assert status["status"] == AutoLoopTaskStatus.RUNNING.value
    await engine.stop()


@pytest.mark.asyncio
async def test_task_completes(engine):
    await engine.start()
    task_id = engine.start_task("test", max_steps=2)
    await asyncio.sleep(0.5)
    status = await engine.get_status(task_id)
    assert status["status"] == AutoLoopTaskStatus.COMPLETED.value
    await engine.stop()


@pytest.mark.asyncio
async def test_cancel_task(engine):
    await engine.start()
    task_id = engine.start_task("test", max_steps=100)
    engine._tasks[task_id]
    await engine.stop()  # This cancels running tasks
    status = await engine.get_status(task_id)
    assert status["status"] == AutoLoopTaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_runner_registration(engine):
    called = False

    async def custom_runner(record):
        nonlocal called
        called = True
        record.current_step = record.max_steps - 1

    engine.register_runner("autonomous", custom_runner)
    await engine.start()
    task_id = engine.start_task("test")
    await asyncio.sleep(0.2)
    assert called is True
    status = await engine.get_status(task_id)
    assert status["status"] == AutoLoopTaskStatus.COMPLETED.value
    await engine.stop()


@pytest.mark.asyncio
async def test_get_status_missing(engine):
    assert await engine.get_status("missing") is None


@pytest.mark.asyncio
async def test_recover_interrupted_sessions():

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    test_session = async_sessionmaker(test_engine, class_=__import__("sqlalchemy.ext.asyncio", fromlist=["AsyncSession"]).AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session() as db:
        db.add(AutoLoopTask(id="recover-1", objective="recover me", status="running", max_steps=5, current_step=2))
        db.add(AutoLoopTask(id="recover-2", objective="done", status="completed", max_steps=5, current_step=5))
        await db.commit()

        engine = AutoLoopEngine()
        # Patch async_session to use our test session
        with patch("app.core.auto_loop.async_session", test_session):
            count = await engine.recover_interrupted_sessions()

        assert count == 1
        assert "recover-1" in engine._tasks
        # Recovered tasks are launched immediately, so they transition to RUNNING
        await asyncio.sleep(0.1)
        assert engine._tasks["recover-1"].status == AutoLoopTaskStatus.RUNNING
        assert engine._tasks["recover-1"].current_step == 2
