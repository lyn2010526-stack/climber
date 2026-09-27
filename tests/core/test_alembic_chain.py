"""Regression coverage for running the complete migration chain on SQLite."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_head_succeeds_on_clean_sqlite(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database) as connection:
        columns = {
            row[1]: row[4]
            for row in connection.execute("PRAGMA table_info(sessions)")
        }
        assert "model_settings" in columns
        assert columns["model_settings"] is None
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "f6a7b8c9d0e1"
