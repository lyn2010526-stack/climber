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

from app.config import settings  # noqa: E402

# Offline ``--sql`` mode only renders DDL; it never connects, so no DBAPI driver
# is needed. Importing app.storage would otherwise eagerly build the async
# engine and fail on a non-sqlite URL whose driver is not installed. Point the
# storage module at an in-memory sqlite URL for the import only, then hand the
# real URL to Alembic below.
_offline_sql = context.is_offline_mode()
_real_database_url = settings.database_url
if _offline_sql and not _real_database_url.startswith("sqlite"):
    settings.database_url = "sqlite+aiosqlite:///:memory:"

from app.storage import (  # noqa: E402
    Base,
    database,  # noqa: F401
    models_cost,  # noqa: F401
    models_eval,  # noqa: F401
    models_feedback,  # noqa: F401
    models_files,  # noqa: F401
    models_groups,  # noqa: F401
    models_instruction_traces,  # noqa: F401
    models_memory,  # noqa: F401
    models_memory_archive,  # noqa: F401
    models_platform,  # noqa: F401
    models_plugins,  # noqa: F401
    models_reasoning,  # noqa: F401
    models_skills,  # noqa: F401
    models_traces,  # noqa: F401
)

if _offline_sql and not _real_database_url.startswith("sqlite"):
    settings.database_url = _real_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _is_sqlite(url: str | None) -> bool:
    return bool(url) and url.startswith("sqlite")


def run_migrations_offline() -> None:
    # The application setting is the single source of truth; the literal value
    # in alembic.ini is only a placeholder for tooling that requires one. This
    # keeps offline ``--sql`` on the same dialect as the online path.
    url = settings.database_url or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite(url),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    # The application setting is the single source of truth online; the literal
    # value in alembic.ini is only a placeholder for tooling that requires one.
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
