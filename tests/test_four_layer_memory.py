"""Tests for four-layer memory (short, medium, long, FTS5)."""

from __future__ import annotations

import pytest

from app.core.four_layer_memory import (
    LongTermMemory,
    MediumTermMemory,
    ShortTermMemory,
    search_memory,
)


def test_short_term_sliding_window():
    m = ShortTermMemory(window_size=3)
    for i in range(5):
        m.add("user", f"msg_{i}")
    assert len(m.turns) == 3
    assert m.turns[-1].content == "msg_4"
    assert m.turns[0].content == "msg_2"


def test_short_term_evicted():
    m = ShortTermMemory(window_size=2)
    for i in range(4):
        m.add("user", f"msg_{i}")
    evicted = m.evicted()
    assert len(evicted) == 2
    assert evicted[0].content == "msg_0"


def test_medium_term_lifecycle():
    m = MediumTermMemory()
    task_id = m.begin_task("test task")
    m.add_record("click button", result="ok")
    m.add_record("read text", result="hello")
    assert m.get_active() is not None
    assert m.get_active().operation_count == 2
    finished = asyncio.run(m.finish_task(archive=True))
    assert finished is not None
    assert m.get_active() is None
    history = m.get_task_history(task_id)
    assert len(history) == 2


@pytest.mark.asyncio
async def test_long_term_snapshot_and_proposal(tmp_path):
    m = LongTermMemory(base_dir=str(tmp_path / "ltm"))
    snap = m.snapshot()
    assert "MEMORY.md" in snap
    assert "USER.md" in snap

    proposal = m.propose_memory_update("# MEMORY.md\n\nnew fact", reason="test")
    assert proposal.has_changes
    assert "new fact" in proposal.diff
    # not approved yet
    assert m.apply_proposal(proposal) is False
    proposal.approved = True
    assert m.apply_proposal(proposal) is True
    assert "new fact" in m.read_memory()


def test_fts5_index(tmp_path):
    from app.core.four_layer_memory.fts5_index import FTS5MemoryIndex

    idx = FTS5MemoryIndex(db_path=str(tmp_path / "fts5.db"))
    idx.index("hello world", source="user", session_id="s1", message_id="m1")
    idx.index("goodbye world", source="agent", session_id="s1", message_id="m2")
    results = idx.search("hello", limit=5)
    assert len(results) >= 1
    assert "hello" in results[0]["content"]

    results = idx.search("hello OR goodbye", limit=5)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_memory_async_tool():
    from app.core.four_layer_memory.fts5_index import FTS5MemoryIndex

    idx = FTS5MemoryIndex(db_path="data/test_fts5_async.db")
    idx.index("test data for async search", source="tool", session_id="s1")
    results = await search_memory("test data", limit=5)
    assert len(results) >= 1


import asyncio
