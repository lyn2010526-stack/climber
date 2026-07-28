"""Alembic migration environment for Climber."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add project root to path so ``app`` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage import Base  # noqa: E402
from app.storage import database  # noqa: F401
from app.storage import models_memory  # noqa: F401
from app.storage import models_traces  # noqa: F401
from app.storage import models_eval  # noqa: F401
from app.storage import models_cost  # noqa: F401
from app.storage import models_skills  # noqa: F401
from app.storage import models_groups  # noqa: F401
from app.storage import models_feedback  # noqa: F401
from app.storage import models_files  # noqa: F401
from app.storage import models_plugins  # noqa: F401
from app.storage import models_reasoning  # noqa: F401
from app.storage import models_platform  # noqa: F401

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


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
