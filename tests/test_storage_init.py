"""Tests for storage __init__ module."""

from __future__ import annotations

import unittest.mock as mock

import pytest

from app.storage import _ensure_sqlite_dir


class TestEnsureSqliteDir:
    """Tests for _ensure_sqlite_dir."""

    def test_memory_db_skipped(self):
        result = _ensure_sqlite_dir("sqlite+aiosqlite:///file:memdb?mode=memory&cache=shared&uri=true")
        assert result is None

    def test_file_db_creates_dir(self, tmp_path):
        db_path = tmp_path / "subdir" / "test.db"
        url = f"sqlite+aiosqlite:///{db_path}"
        _ensure_sqlite_dir(url)
        assert (tmp_path / "subdir").exists()

    def test_empty_path_part(self):
        with mock.patch("app.storage.Path") as mock_path:
            _ensure_sqlite_dir("sqlite+aiosqlite:///")
            mock_path.assert_not_called()


class TestDbHealth:
    """Tests for db_health function."""

    @pytest.mark.asyncio
    async def test_connected(self):
        from app.storage import db_health

        mock_conn = mock.MagicMock()
        mock_conn.execute = mock.AsyncMock()
        mock_conn.__aenter__ = mock.AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = mock.AsyncMock(return_value=None)

        mock_engine = mock.MagicMock()
        mock_engine.connect = mock.MagicMock(return_value=mock_conn)

        with mock.patch("app.storage.engine", mock_engine), mock.patch("app.storage._is_sqlite", False):
            result = await db_health()

        assert result["connected"] is True
        assert result["backend"] == "other"

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        from app.storage import db_health

        mock_engine = mock.MagicMock()
        mock_engine.connect = mock.MagicMock(side_effect=ConnectionError("fail"))

        with mock.patch("app.storage.engine", mock_engine), mock.patch("app.storage._is_sqlite", False):
            result = await db_health()

        assert result["connected"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_sqlite_backend(self):
        from app.storage import db_health

        mock_result = mock.MagicMock()
        mock_result.scalar.return_value = "wal"

        mock_conn = mock.MagicMock()
        mock_conn.execute = mock.AsyncMock(return_value=mock_result)
        mock_conn.__aenter__ = mock.AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = mock.AsyncMock(return_value=None)

        mock_engine = mock.MagicMock()
        mock_engine.connect = mock.MagicMock(return_value=mock_conn)

        with mock.patch("app.storage.engine", mock_engine), mock.patch("app.storage._is_sqlite", True):
            result = await db_health()

        assert result["backend"] == "sqlite"
        assert result["connected"] is True
