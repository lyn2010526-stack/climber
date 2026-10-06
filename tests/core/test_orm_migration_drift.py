"""Regression tests for the ORM/migration drift alignment revision.

The initial migration predates several ORM columns. A fresh database built by
``alembic upgrade head`` must match the ORM metadata for the storage tables
called out by the db-storage report (R13-17, R13-18, R13-19, R13-20, R13-21,
R13-22, R13-12, R13-09, R9-16).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

import app.storage
import app.storage.database
import app.storage.models_cost
import app.storage.models_eval
import app.storage.models_feedback
import app.storage.models_files
import app.storage.models_groups
import app.storage.models_instruction_traces
import app.storage.models_memory
import app.storage.models_platform
import app.storage.models_plugins
import app.storage.models_reasoning
import app.storage.models_skills
import app.storage.models_traces

REPO_ROOT = Path(__file__).resolve().parents[2]

TARGET_TABLES = (
    "sessions",
    "documents",
    "agents",
    "skills",
    "user_profiles",
    "agent_group_members",
    "core_memory_blocks",
)


@pytest.fixture(scope="module")
def migrated_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("migration") / "climber.db"
    env = {"DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{db_path}")
    yield engine
    engine.dispose()


def test_migrated_schema_matches_orm_columns(migrated_db) -> None:
    inspector = inspect(migrated_db)
    metadata = app.storage.Base.metadata
    for table in TARGET_TABLES:
        assert table in metadata.tables, table
        orm_columns = {column.name for column in metadata.tables[table].columns}
        db_columns = {column["name"] for column in inspector.get_columns(table)}
        assert not (orm_columns - db_columns), (
            f"{table} ORM-only columns: {orm_columns - db_columns}"
        )


def test_nullable_columns_match_orm(migrated_db) -> None:
    inspector = inspect(migrated_db)
    metadata = app.storage.Base.metadata
    for table in TARGET_TABLES:
        db_columns = {column["name"]: column for column in inspector.get_columns(table)}
        for column in metadata.tables[table].columns:
            if column.name not in db_columns:
                continue
            assert db_columns[column.name]["nullable"] is bool(column.nullable), (
                f"{table}.{column.name} nullable mismatch"
            )


def _unique_key_sets(inspector, table: str) -> set[tuple[str, ...]]:
    keys = {
        tuple(sorted(constraint["column_names"]))
        for constraint in inspector.get_unique_constraints(table)
    }
    for index in inspector.get_indexes(table):
        if index.get("unique"):
            keys.add(tuple(sorted(index["column_names"])))
    return keys


def test_new_unique_constraints_present(migrated_db) -> None:
    inspector = inspect(migrated_db)
    assert ("agent_id", "group_id") in _unique_key_sets(inspector, "agent_group_members")
    assert ("agent_id", "label", "user_id") in _unique_key_sets(inspector, "core_memory_blocks")


def test_user_settings_has_no_users_foreign_key(migrated_db) -> None:
    # R9-16: the ORM declares no FK; the default principal never has a users row.
    fks = inspect(migrated_db).get_foreign_keys("user_settings")
    assert not any(fk.get("referred_table") == "users" for fk in fks)


def test_upgrade_downgrade_round_trip(tmp_path) -> None:
    db_path = tmp_path / "roundtrip.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    for args in (["upgrade", "head"], ["downgrade", "a1b2c3d4e5f7"], ["upgrade", "head"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
