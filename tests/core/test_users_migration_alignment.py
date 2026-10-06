"""Regression tests for R11-H18: the migration-chain users table must match ORM.

The initial migration (dd8212a8f22a) created ``users`` with a ``String(36)``
uuid primary key and a legacy column set, while ``app.models.users.User``
declares an ``Integer`` autoincrement primary key and the full profile column
set. Revision f6a7b8c9d0e1 rebuilds the table on the migration chain; these
tests pin the outcome of ``alembic upgrade head`` against the ORM metadata.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect

import app.storage  # noqa: F401
from app.models.users import User  # noqa: F401  (registers users on Base.metadata)

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_users_columns_match_orm(migrated_db) -> None:
    inspector = inspect(migrated_db)
    orm_columns = {column.name for column in User.__table__.columns}
    db_columns = {column["name"] for column in inspector.get_columns("users")}
    assert db_columns == orm_columns, (
        f"users drift: ORM-only={orm_columns - db_columns}, DB-only={db_columns - orm_columns}"
    )


def test_users_primary_key_is_integer(migrated_db) -> None:
    inspector = inspect(migrated_db)
    columns = {column["name"]: column for column in inspector.get_columns("users")}
    id_type = columns["id"]["type"]
    assert "INTEGER" in str(id_type).upper(), f"users.id type drift: {id_type!r}"
    assert columns["id"]["nullable"] is False


def test_users_nullability_matches_orm(migrated_db) -> None:
    inspector = inspect(migrated_db)
    db_columns = {column["name"]: column for column in inspector.get_columns("users")}
    for column in User.__table__.columns:
        assert db_columns[column.name]["nullable"] is bool(column.nullable), (
            f"users.{column.name} nullable mismatch: "
            f"db={db_columns[column.name]['nullable']} orm={column.nullable}"
        )


def test_users_unique_indexes_present(migrated_db) -> None:
    inspector = inspect(migrated_db)
    unique_indexes = {
        index["name"]
        for index in inspector.get_indexes("users")
        if index.get("unique")
    }
    assert "ix_users_username" in unique_indexes
    assert "ix_users_email" in unique_indexes


def test_users_insert_assigns_integer_id(migrated_db) -> None:
    """The migrated table must behave like the ORM-built one (rowid autoincrement)."""
    with migrated_db.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (username, email, hashed_password) "
                "VALUES ('mig-tester', 'mig-tester@example.com', 'hash')"
            )
        )
        row = conn.execute(
            sa.text("SELECT id, role, status FROM users WHERE username = 'mig-tester'")
        ).one()
    assert isinstance(row.id, int)
    assert row.role == "viewer"
    assert row.status == "active"


def test_upgrade_downgrade_round_trip(tmp_path) -> None:
    db_path = tmp_path / "roundtrip.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    for args in (["upgrade", "head"], ["downgrade", "f5a6b7c8d9e0"], ["upgrade", "head"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    inspector = inspect(create_engine(f"sqlite:///{db_path}"))
    db_columns = {column["name"] for column in inspector.get_columns("users")}
    assert db_columns == {column.name for column in User.__table__.columns}


def test_create_all_shaped_database_is_untouched(tmp_path) -> None:
    """Databases built by ``Base.metadata.create_all`` pass through as a no-op."""
    db_path = tmp_path / "createall.db"
    engine = create_engine(f"sqlite:///{db_path}")
    User.__table__.metadata.create_all(engine, tables=[User.__table__])
    before = inspect(engine).get_columns("users")
    before_sql = engine.connect().execute(
        sa.text("SELECT sql FROM sqlite_master WHERE name = 'users'")
    ).scalar()
    engine.dispose()

    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "stamp", "f5a6b7c8d9e0"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{db_path}")
    after = inspect(engine).get_columns("users")
    after_sql = engine.connect().execute(
        sa.text("SELECT sql FROM sqlite_master WHERE name = 'users'")
    ).scalar()
    engine.dispose()

    def _normalized(columns: list[dict]) -> list[dict]:
        # TypeEngine instances do not implement value equality; compare the
        # rendered type instead of object identity.
        return [
            {key: (str(value) if key == "type" else value) for key, value in column.items()}
            for column in columns
        ]

    assert _normalized(after) == _normalized(before), (
        "create_all-shaped users table was modified by the migration"
    )
    assert after_sql == before_sql
