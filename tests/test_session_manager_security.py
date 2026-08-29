"""Security regression tests for checkpoint session paths."""

from pathlib import Path

import pytest

from app.core.session_manager import SessionManager


@pytest.fixture
def manager(tmp_path: Path) -> SessionManager:
    return SessionManager(str(tmp_path / "sessions"))


def test_checkpoint_rejects_path_traversal(manager: SessionManager):
    with pytest.raises(ValueError, match="Invalid session id"):
        manager.save_checkpoint("../outside", [], 0)


def test_checkpoint_rejects_absolute_path(manager: SessionManager):
    with pytest.raises(ValueError, match="Invalid session id"):
        manager.get_latest_checkpoint("/tmp/outside")


def test_checkpoint_uses_storage_root(manager: SessionManager):
    manager.save_checkpoint("session-1", [{"role": "user", "content": "hello"}], 1)

    assert (manager._storage / "session-1" / "latest.json").exists()


def test_fork_rejects_path_traversal(manager: SessionManager):
    manager.save_checkpoint("source", [], 0)

    with pytest.raises(ValueError, match="Invalid session id"):
        manager.fork_session("source", "../outside")


def test_delete_rejects_path_traversal(manager: SessionManager):
    with pytest.raises(ValueError, match="Invalid session id"):
        manager.delete_session("../outside")
