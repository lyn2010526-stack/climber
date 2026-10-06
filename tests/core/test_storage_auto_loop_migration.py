"""Regression tests for the sqlite auto-migration of auto_loop_task columns.

An existing database created before the retry/interruption/checkpoint fields
landed keeps its old column set, because create_all never alters existing
tables. init_db must add the missing columns so AutoLoopTask SELECTs (and
therefore GET /api/v1/tasks/) work instead of raising OperationalError.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.storage import _ensure_auto_loop_columns

OLD_COLUMNS = """
CREATE TABLE auto_loop_tasks (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    owner_id VARCHAR(36) NOT NULL,
    objective TEXT NOT NULL,
    status VARCHAR(20),
    max_steps INTEGER,
    current_step INTEGER,
    result JSON,
    error TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    started_at DATETIME,
    finished_at DATETIME,
    heartbeat_at DATETIME
)
"""


@pytest.mark.asyncio
async def test_ensure_auto_loop_columns_adds_all_four_missing_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text(OLD_COLUMNS))
    async with engine.begin() as conn:
        await _ensure_auto_loop_columns(conn)
    async with engine.connect() as conn:
        from sqlalchemy import inspect

        columns = await conn.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("auto_loop_tasks")
            }
        )
    assert {"retry_count", "interruption_reason", "checkpoint", "progress_evaluation"} <= columns
    await engine.dispose()


@pytest.mark.asyncio
async def test_ensure_auto_loop_columns_is_idempotent(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text(OLD_COLUMNS))
    for _ in range(2):
        async with engine.begin() as conn:
            await _ensure_auto_loop_columns(conn)
    async with engine.connect() as conn:
        from sqlalchemy import inspect

        names = [
            column["name"]
            for column in await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_columns("auto_loop_tasks")
            )
        ]
    assert names.count("retry_count") == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_ensure_auto_loop_columns_noop_when_table_missing(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'empty.db'}")
    async with engine.begin() as conn:
        await _ensure_auto_loop_columns(conn)
    await engine.dispose()
