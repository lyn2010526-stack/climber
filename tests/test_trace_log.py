"""Tests for append-only trace log (all event types + rotation + capabilities)."""

from __future__ import annotations

import pytest

from app.core.trace_log import (
    EVENT_CONTEXT_INJECTION,
    EVENT_DECISION,
    EVENT_MODEL_SWITCH,
    EVENT_SKILL_LOAD,
    EVENT_SUBAGENT,
    EVENT_SYSTEM_PROMPT,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    TraceLog,
)


@pytest.mark.asyncio
async def test_append_and_read_roundtrip(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    ev = await log.append(EVENT_TOOL_CALL, {"name": "ls", "params": {"dir": "/tmp"}}, session_id="s1")
    assert ev.event_id
    assert ev.sequence == 1
    assert ev.session_id == "s1"

    events = await log.read("s1")
    assert len(events) == 1
    assert events[0].event_type == EVENT_TOOL_CALL
    assert events[0].data["name"] == "ls"


@pytest.mark.asyncio
async def test_append_is_immutable_append_only(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    for i in range(5):
        await log.append(EVENT_DECISION, {"action": f"a{i}"}, session_id="s1")
    raw = (tmp_path / "traces" / "s1.jsonl").read_text(encoding="utf-8")
    assert raw.count("\n") == 5


@pytest.mark.asyncio
async def test_all_event_types_can_be_written(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    for ev_type in (
        EVENT_SYSTEM_PROMPT,
        EVENT_TOOL_CALL,
        EVENT_TOOL_RESULT,
        EVENT_DECISION,
        EVENT_MODEL_SWITCH,
        EVENT_SUBAGENT,
        EVENT_CONTEXT_INJECTION,
        EVENT_SKILL_LOAD,
    ):
        await log.append(ev_type, {"note": "x"}, session_id="s1")
    events = await log.read("s1")
    types = {e.event_type for e in events}
    assert types == {
        EVENT_SYSTEM_PROMPT,
        EVENT_TOOL_CALL,
        EVENT_TOOL_RESULT,
        EVENT_DECISION,
        EVENT_MODEL_SWITCH,
        EVENT_SUBAGENT,
        EVENT_CONTEXT_INJECTION,
        EVENT_SKILL_LOAD,
    }


@pytest.mark.asyncio
async def test_search_and_filter(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    await log.append(EVENT_TOOL_CALL, {"name": "read_file"}, session_id="s1")
    await log.append(EVENT_TOOL_CALL, {"name": "write_file"}, session_id="s1")

    found = await log.search("write_file", session_id="s1")
    assert len(found) == 1
    assert found[0].data["name"] == "write_file"

    by_type = await log.read("s1", event_type=EVENT_DECISION)
    assert by_type == []


@pytest.mark.asyncio
async def test_fork_creates_new_session(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    for i in range(4):
        await log.append(EVENT_TOOL_CALL, {"name": f"t{i}"}, session_id="src")
    count = await log.fork("src", after_sequence=2, new_session_id="forked")
    assert count == 2  # events seq 3 and 4 (after seq 2)
    forked = await log.read("forked")
    assert len(forked) == 2


@pytest.mark.asyncio
async def test_trajectory_view(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"))
    await log.append(EVENT_TOOL_CALL, {"name": "ls"}, session_id="s1")
    await log.append(EVENT_DECISION, {"action": "open", "target": "app", "confidence": 0.9}, session_id="s1")
    traj = await log.trajectory("s1")
    assert len(traj) == 2
    assert traj[0]["event_type"] == EVENT_TOOL_CALL
    assert "tool_call" in traj[0]["summary"]


@pytest.mark.asyncio
async def test_rotation_when_file_exceeds_cap(tmp_path):
    log = TraceLog(base_dir=str(tmp_path / "traces"), max_file_bytes=120)
    for i in range(20):
        await log.append(EVENT_TOOL_CALL, {"name": "x" * 50, "seq": i}, session_id="rot")
    # after rotation events are still readable across rotated + current files?
    events = await log.read("rot")
    # The active file continues; rotation archives but reading only reads the
    # current session file. Reading should still return the current file's events.
    assert len(events) > 0
