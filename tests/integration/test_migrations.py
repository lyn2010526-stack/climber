from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from app.models import users as models_users  # noqa: F401
from app.storage import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEAD_REVISION = "b2c3d4e5f6a7"


def _run_alembic(database_path: Path, *arguments: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "APP_TESTING": "true",
            "TEST_DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _revision(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def test_migrations_round_trip_on_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "fresh.db"

    _run_alembic(database_path, "upgrade", "head")

    with sqlite3.connect(database_path) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        users_columns = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(users)")}
        settings_foreign_keys = connection.execute("PRAGMA foreign_key_list(user_settings)").fetchall()
    assert _revision(database_path) == HEAD_REVISION
    assert {"users", "auth_api_keys", "user_settings"}.issubset(tables)
    assert users_columns["id"] == "INTEGER"
    assert users_columns["hashed_password"] == "VARCHAR(256)"
    assert settings_foreign_keys[0][2:5] == ("users", "user_id", "id")

    _run_alembic(database_path, "downgrade", "base")
    _run_alembic(database_path, "upgrade", "head")

    assert _revision(database_path) == HEAD_REVISION


def test_upgrade_adopts_existing_current_schema_without_version_table(tmp_path: Path) -> None:
    database_path = tmp_path / "existing.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE user_settings ("
                "id VARCHAR(36) PRIMARY KEY, user_id INTEGER NOT NULL UNIQUE, "
                "autonomous_agent_mode BOOLEAN NOT NULL, "
                "token_throttle_mcp_enabled BOOLEAN NOT NULL, "
                "enhanced_prompt_enabled BOOLEAN NOT NULL, "
                "code_review_graph_enabled BOOLEAN NOT NULL DEFAULT 0, "
                "mcp_status VARCHAR(20) NOT NULL DEFAULT 'disconnected', "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "FOREIGN KEY(user_id) REFERENCES users(id))"
            )
        )
    engine.dispose()

    _run_alembic(database_path, "upgrade", "head")

    assert _revision(database_path) == HEAD_REVISION
