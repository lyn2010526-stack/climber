"""Alembic migration environment for Climber."""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add project root to path so ``app`` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage import (
    Base,  # noqa: E402
    database,  # noqa: F401
    models_cost,  # noqa: F401
    models_eval,  # noqa: F401
    models_feedback,  # noqa: F401
    models_files,  # noqa: F401
    models_groups,  # noqa: F401
    models_memory,  # noqa: F401
    models_platform,  # noqa: F401
    models_plugins,  # noqa: F401
    models_reasoning,  # noqa: F401
    models_skills,  # noqa: F401
    models_traces,  # noqa: F401
)
from app.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
