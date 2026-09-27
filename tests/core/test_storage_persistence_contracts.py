"""Focused contracts for cache and SQLite persistence boundaries."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app.storage.cache import Cache


@pytest.mark.asyncio
async def test_cache_preserves_falsey_json_values() -> None:
    redis = AsyncMock()
    redis.get.return_value = "false"

    assert await Cache(redis).get("flag") is False
    redis.get.assert_awaited_once_with("ae:flag")


@pytest.mark.asyncio
async def test_close_redis_prefers_async_close(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.storage.cache as cache_module

    client = AsyncMock()
    client.aclose = AsyncMock()
    client.close = AsyncMock()
    monkeypatch.setattr(cache_module, "_redis_client", client)

    await cache_module.close_redis()

    client.aclose.assert_awaited_once_with()
    client.close.assert_not_awaited()
    assert cache_module._redis_client is None


@pytest.mark.asyncio
async def test_checkpoint_schema_bootstrap_creates_missing_table() -> None:
    from app.storage.database import ensure_checkpoint_schema

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        await ensure_checkpoint_schema(engine)
        async with engine.connect() as connection:
            exists = await connection.run_sync(
                lambda sync_connection: sync_connection.dialect.has_table(
                    sync_connection, "checkpoints"
                )
            )
        assert exists
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_checkpoint_schema_bootstrap_is_safe_when_called_concurrently() -> None:
    from app.storage.database import CheckpointRecord, ensure_checkpoint_schema

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        await asyncio.gather(*(ensure_checkpoint_schema(engine) for _ in range(8)))
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: {
                    column["name"]
                    for column in inspect(sync_connection).get_columns("checkpoints")
                }
            )
        assert columns >= {
            "channel_values",
            "channel_versions",
            "versions_seen",
            "pending_writes",
        }
        assert CheckpointRecord.__table__.indexes
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_propagates_schema_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.storage as storage_module

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    def fail_create_all(_connection) -> None:
        raise RuntimeError("schema bootstrap failed")

    monkeypatch.setattr(storage_module, "engine", engine)
    monkeypatch.setattr(storage_module.Base.metadata, "create_all", fail_create_all)
    try:
        with pytest.raises(RuntimeError, match="schema bootstrap failed"):
            await storage_module.init_db()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_connections_commit_concurrent_checkpoint_writes() -> None:
    from app.storage import async_session, engine
    from app.storage.database import CheckpointRecord, ensure_checkpoint_schema

    session_id = "storage-concurrent-write-test"
    await ensure_checkpoint_schema(engine)
    async with async_session() as db:
        await db.execute(delete(CheckpointRecord).where(CheckpointRecord.session_id == session_id))
        await db.commit()

    async def write_checkpoint(index: int) -> None:
        async with async_session() as db:
            db.add(
                CheckpointRecord(
                    id=f"{session_id}-{index}",
                    session_id=session_id,
                    thread_id="thread",
                    messages="[]",
                    iteration=index,
                    status="running",
                )
            )
            await db.commit()

    try:
        await asyncio.gather(*(write_checkpoint(index) for index in range(8)))
        async with async_session() as db:
            count = await db.scalar(
                select(func.count())
                .select_from(CheckpointRecord)
                .where(CheckpointRecord.session_id == session_id)
            )
        assert count == 8
    finally:
        async with async_session() as db:
            await db.execute(delete(CheckpointRecord).where(CheckpointRecord.session_id == session_id))
            await db.commit()


@pytest.mark.asyncio
async def test_auto_loop_task_persists_owner_id_and_user_id_alias() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.storage import Base
    from app.storage.models_platform import AutoLoopTask

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all, tables=[AutoLoopTask.__table__])
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            task = AutoLoopTask(objective="run", owner_id="user-1")
            session.add(task)
            await session.commit()
            assert task.user_id == "user-1"
            persisted = await session.scalar(select(AutoLoopTask).where(AutoLoopTask.id == task.id))
            assert persisted is not None
            assert persisted.owner_id == "user-1"
        async with engine.connect() as connection:
            indexes = await connection.run_sync(
                lambda sync_connection: {
                    index["name"] for index in inspect(sync_connection).get_indexes("auto_loop_tasks")
                }
            )
        assert "ix_auto_loop_tasks_owner_id" in indexes
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auto_loop_task_legacy_row_keeps_nullable_owner_id() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.storage import Base
    from app.storage.models_platform import AutoLoopTask

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all, tables=[AutoLoopTask.__table__])
            await connection.execute(
                text(
                    "INSERT INTO auto_loop_tasks "
                    "(id, objective, status, max_steps, current_step) "
                    "VALUES ('legacy-task', '{\"objective\": \"run\"}', 'pending', 10, 0)"
                )
            )
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            task = await session.get(AutoLoopTask, "legacy-task")
            assert task is not None
            assert task.owner_id is None
            assert task.user_id is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_owner_id_migration_backfills_legacy_objective_owner() -> None:
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy.ext.asyncio import create_async_engine

    migration_path = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "f6a7b8c9d0e1_add_owner_id_to_auto_loop_tasks.py"
    )
    spec = importlib.util.spec_from_file_location("owner_id_migration", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE auto_loop_tasks ("
                    "id VARCHAR(36) PRIMARY KEY, objective TEXT NOT NULL, "
                    "status VARCHAR(20) NOT NULL, max_steps INTEGER NOT NULL, "
                    "current_step INTEGER NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO auto_loop_tasks "
                    "(id, objective, status, max_steps, current_step) "
                    "VALUES ('legacy-task', '{\"_owner_id\": \"user-2\"}', 'pending', 10, 0)"
                )
            )

            def run_migration(sync_connection) -> None:
                context = MigrationContext.configure(sync_connection)
                with Operations.context(context):
                    migration.upgrade()

            await connection.run_sync(run_migration)
            result = await connection.execute(
                text("SELECT owner_id FROM auto_loop_tasks WHERE id = 'legacy-task'")
            )
            assert result.scalar_one() == "user-2"
    finally:
        await engine.dispose()
