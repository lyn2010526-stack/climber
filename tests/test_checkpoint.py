"""Tests for checkpoint storage."""

from __future__ import annotations

import pytest

from app.core.checkpoint import (
    CheckpointData,
    InMemoryCheckpointStore,
    PendingWrite,
    SQLiteCheckpointStore,
)


class TestCheckpointData:
    """Tests for CheckpointData dataclass."""

    def test_default_values(self):
        cp = CheckpointData(
            session_id="s1",
            messages=[{"role": "user", "content": "hi"}],
            iteration=1,
            status="running",
        )
        assert cp.session_id == "s1"
        assert cp.messages == [{"role": "user", "content": "hi"}]
        assert cp.iteration == 1
        assert cp.status == "running"
        assert cp.tool_results == []
        assert cp.metadata == {}
        assert cp.channel_values == {}
        assert cp.channel_versions == {}
        assert cp.versions_seen == {}
        assert cp.pending_writes == []

    def test_custom_values(self):
        cp = CheckpointData(
            session_id="s2",
            messages=[],
            iteration=5,
            status="completed",
            tool_results=[{"tool": "echo", "result": "ok"}],
            metadata={"key": "value"},
            channel_values={"v1": 42},
            channel_versions={"v1": 3},
            versions_seen={"node1": {"v1": 2}},
            pending_writes=[PendingWrite(channel="c1", value="v", write_id="w1")],
        )
        assert cp.tool_results == [{"tool": "echo", "result": "ok"}]
        assert cp.metadata == {"key": "value"}
        assert cp.channel_values == {"v1": 42}
        assert cp.channel_versions == {"v1": 3}
        assert cp.versions_seen == {"node1": {"v1": 2}}
        assert len(cp.pending_writes) == 1


class TestPendingWrite:
    """Tests for PendingWrite dataclass."""

    def test_default_status(self):
        pw = PendingWrite(channel="c1", value="v", write_id="w1")
        assert pw.status == "pending"
        assert pw.channel == "c1"
        assert pw.value == "v"
        assert pw.write_id == "w1"

    def test_custom_status(self):
        pw = PendingWrite(channel="c1", value="v", write_id="w1", status="committed")
        assert pw.status == "committed"


class TestInMemoryCheckpointStore:
    """Tests for InMemoryCheckpointStore."""

    @pytest.mark.asyncio
    async def test_save_and_get(self):
        store = InMemoryCheckpointStore()
        cp = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        await store.save(None, cp, checkpoint_id="cp-1")
        result = await store.get(None, "cp-1")
        assert result is not None
        assert result.session_id == "s1"
        assert result.iteration == 1

    @pytest.mark.asyncio
    async def test_save_generates_id(self):
        store = InMemoryCheckpointStore()
        cp = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        cid = await store.save(None, cp)
        assert cid.startswith("cp-")

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        store = InMemoryCheckpointStore()
        result = await store.get(None, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest(self):
        store = InMemoryCheckpointStore()
        cp1 = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        cp2 = CheckpointData(session_id="s1", messages=[], iteration=3, status="running")
        cp3 = CheckpointData(session_id="s1", messages=[], iteration=2, status="running")
        await store.save(None, cp1, checkpoint_id="cp-1")
        await store.save(None, cp2, checkpoint_id="cp-2")
        await store.save(None, cp3, checkpoint_id="cp-3")
        result = await store.get_latest(None, "s1")
        assert result is not None
        data, cid = result
        assert data.iteration == 3
        assert cid == "cp-2"

    @pytest.mark.asyncio
    async def test_get_latest_nonexistent_session(self):
        store = InMemoryCheckpointStore()
        result = await store.get_latest(None, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_for_session(self):
        store = InMemoryCheckpointStore()
        cp1 = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        cp2 = CheckpointData(session_id="s1", messages=[], iteration=2, status="running")
        cp3 = CheckpointData(session_id="s2", messages=[], iteration=1, status="running")
        await store.save(None, cp1, checkpoint_id="cp-1")
        await store.save(None, cp2, checkpoint_id="cp-2")
        await store.save(None, cp3, checkpoint_id="cp-3")
        result = await store.list_for_session(None, "s1")
        assert len(result) == 2
        assert "cp-1" in result
        assert "cp-2" in result

    @pytest.mark.asyncio
    async def test_list_for_session_nonexistent(self):
        store = InMemoryCheckpointStore()
        result = await store.list_for_session(None, "nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_for_session(self):
        store = InMemoryCheckpointStore()
        cp1 = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        cp2 = CheckpointData(session_id="s1", messages=[], iteration=2, status="running")
        cp3 = CheckpointData(session_id="s2", messages=[], iteration=1, status="running")
        await store.save(None, cp1, checkpoint_id="cp-1")
        await store.save(None, cp2, checkpoint_id="cp-2")
        await store.save(None, cp3, checkpoint_id="cp-3")
        count = await store.delete_for_session(None, "s1")
        assert count == 2
        assert await store.get(None, "cp-1") is None
        assert await store.get(None, "cp-2") is None
        assert await store.get(None, "cp-3") is not None

    @pytest.mark.asyncio
    async def test_delete_for_session_nonexistent(self):
        store = InMemoryCheckpointStore()
        count = await store.delete_for_session(None, "nonexistent")
        assert count == 0

    @pytest.mark.asyncio
    async def test_put_and_get_writes(self):
        store = InMemoryCheckpointStore()
        cp = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        await store.save(None, cp, checkpoint_id="cp-1")
        writes = [
            PendingWrite(channel="c1", value="v1", write_id="w1"),
            PendingWrite(channel="c2", value="v2", write_id="w2", status="committed"),
        ]
        await store.put_writes("cp-1", writes)
        result = await store.get_writes("cp-1")
        assert len(result) == 2
        assert result[0].channel == "c1"
        assert result[1].status == "committed"

    @pytest.mark.asyncio
    async def test_get_writes_nonexistent(self):
        store = InMemoryCheckpointStore()
        result = await store.get_writes("nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_put_writes_accumulates(self):
        store = InMemoryCheckpointStore()
        cp = CheckpointData(session_id="s1", messages=[], iteration=1, status="running")
        await store.save(None, cp, checkpoint_id="cp-w")
        await store.put_writes("cp-w", [PendingWrite(channel="c1", value="v", write_id="w1")])
        await store.put_writes("cp-w", [PendingWrite(channel="c2", value="v", write_id="w2")])
        result = await store.get_writes("cp-w")
        assert len(result) == 2


class TestSQLiteCheckpointStore:
    """Tests for SQLiteCheckpointStore using mocked database."""

    @pytest.mark.asyncio
    async def test_to_checkpoint_parses_json(self):
        """Test _to_checkpoint JSON parsing."""
        store = SQLiteCheckpointStore.__new__(SQLiteCheckpointStore)
        mock_record = type("Record", (), {
            "session_id": "s1",
            "messages": '[{"role":"user","content":"hi"}]',
            "tool_results": '[]',
            "metadata_": '{"key":"value"}',
            "iteration": 1,
            "status": "running",
        })()
        result = store._to_checkpoint(mock_record)
        assert result.session_id == "s1"
        assert result.messages == [{"role": "user", "content": "hi"}]
        assert result.iteration == 1
        assert result.status == "running"
        assert result.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_to_checkpoint_handles_invalid_json(self):
        """Test _to_checkpoint with invalid JSON."""
        store = SQLiteCheckpointStore.__new__(SQLiteCheckpointStore)
        mock_record = type("Record", (), {
            "session_id": "s1",
            "messages": "invalid json",
            "tool_results": "invalid",
            "metadata_": "not json",
            "iteration": 0,
            "status": "unknown",
        })()
        result = store._to_checkpoint(mock_record)
        assert result.messages == []
        assert result.tool_results == []
        assert result.metadata == {}

    @pytest.mark.asyncio
    async def test_to_checkpoint_pending_writes(self):
        """Test _to_checkpoint with pending writes in metadata."""
        import json
        store = SQLiteCheckpointStore.__new__(SQLiteCheckpointStore)
        metadata = {
            "pending_writes": [
                {"channel": "c1", "value": "v", "write_id": "w1", "status": "pending"}
            ]
        }
        mock_record = type("Record", (), {
            "session_id": "s1",
            "messages": "[]",
            "tool_results": "[]",
            "metadata_": json.dumps(metadata),
            "iteration": 1,
            "status": "running",
        })()
        result = store._to_checkpoint(mock_record)
        assert len(result.pending_writes) == 1
        assert result.pending_writes[0].channel == "c1"
        assert "pending_writes" not in result.metadata

    @pytest.mark.asyncio
    async def test_to_checkpoint_empty_metadata(self):
        """Test _to_checkpoint with empty metadata."""
        store = SQLiteCheckpointStore.__new__(SQLiteCheckpointStore)
        mock_record = type("Record", (), {
            "session_id": "s1",
            "messages": "[]",
            "tool_results": "[]",
            "metadata_": "{}",
            "iteration": 0,
            "status": "idle",
        })()
        result = store._to_checkpoint(mock_record)
        assert result.metadata == {}
        assert result.pending_writes == []
