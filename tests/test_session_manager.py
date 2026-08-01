# tests/test_session_manager.py
import pytest
from app.core.session_manager import SessionManager

@pytest.fixture
def mgr(tmp_path):
    return SessionManager(storage_dir=str(tmp_path / "sessions"))

def test_save_and_load_checkpoint(mgr):
    mgr.save_checkpoint(
        session_id="s1",
        messages=[{"role": "user", "content": "hello"}],
        iteration=1,
        status="active",
    )
    checkpoint = mgr.get_latest_checkpoint("s1")
    assert checkpoint is not None
    assert checkpoint["session_id"] == "s1"
    assert len(checkpoint["messages"]) == 1

def test_resume_session(mgr):
    mgr.save_checkpoint(
        session_id="s2",
        messages=[{"role": "user", "content": "start"}],
        iteration=0,
    )
    mgr.save_checkpoint(
        session_id="s2",
        messages=[{"role": "user", "content": "start"}, {"role": "assistant", "content": "ok"}],
        iteration=1,
    )
    state = mgr.resume_session("s2")
    assert state is not None
    assert state["iteration"] == 1
    assert len(state["messages"]) == 2

def test_list_sessions(mgr):
    mgr.save_checkpoint("a", [], 0)
    mgr.save_checkpoint("b", [], 0)
    sessions = mgr.list_sessions()
    assert len(sessions) >= 2
    ids = [s["session_id"] for s in sessions]
    assert "a" in ids and "b" in ids

def test_fork_session(mgr):
    mgr.save_checkpoint("original", [{"role": "user", "content": "q"}], 1)
    fork_id = mgr.fork_session("original", new_session_id="fork-1")
    assert fork_id == "fork-1"
    state = mgr.get_latest_checkpoint("fork-1")
    assert state is not None
    assert state["parent_session"] == "original"
