"""Tests for RAG embedding wiring and L1/L2 self-learning event loops."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.event_bus import EventBus
from app.core.integration.event_store import EventStore
from app.core.self_learning.l2_distill import BackgroundDistiller
from app.core.self_learning.wiring import wire_self_learning
from app.core.skill_store.skill_store import SkillMetadata, SkillStore


def _make_store(tmp_path) -> SkillStore:
    store = SkillStore(base_dir=str(tmp_path / "skills"))
    store.create(
        "read_file",
        SkillMetadata(name="read_file", description="reads files"),
        "# read_file\n\n## Steps\n1. open the file\n",
    )
    return store


class _FakeL1:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def fix(self, skill_id: str, error: str, old_instruction: str) -> tuple[bool, str]:
        self.calls.append((skill_id, error, old_instruction))
        return True, old_instruction + "\npatched"


@pytest.mark.asyncio
async def test_l1_fixes_skill_on_tool_error(tmp_path):
    store = _make_store(tmp_path)
    l1 = _FakeL1()
    l2 = BackgroundDistiller(store=store)
    bus = EventBus()

    wire_self_learning(l1, l2, store, bus)
    await bus.publish(
        "tool_result",
        {"tool_name": "read_file", "error": "element not found", "result": ""},
    )

    assert len(l1.calls) == 1
    skill_id, error, old_instruction = l1.calls[0]
    assert skill_id == "read_file"
    assert error == "element not found"
    assert "open the file" in old_instruction


@pytest.mark.asyncio
async def test_l1_ignores_successes_and_unknown_skills(tmp_path):
    store = _make_store(tmp_path)
    l1 = _FakeL1()
    bus = EventBus()

    wire_self_learning(l1, BackgroundDistiller(store=store), store, bus)
    await bus.publish("tool_result", {"tool_name": "read_file", "error": "", "result": "ok"})
    await bus.publish("tool_result", {"tool_name": "unknown_tool", "error": "boom", "result": ""})

    assert l1.calls == []


@pytest.mark.asyncio
async def test_l2_distills_completed_session(tmp_path):
    store = _make_store(tmp_path)
    events = EventStore(tmp_path / "events.db")

    class _FakeL2:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[Any]]] = []

        async def distill(self, task_title: str, operations: list[Any], app_list: Any = None) -> Any:
            self.calls.append((task_title, operations))

    l2 = _FakeL2()
    bus = EventBus()
    wire_self_learning(_FakeL1(), l2, store, bus, event_store=events)

    await events.append("message", {"role": "user", "content": "organize downloads"}, stream_id="s1")
    for i in range(3):
        await events.append("tool_call", {"name": f"read_file_{i}"}, stream_id="s1")
    await events.append("done", {"status": "completed"}, stream_id="s1")

    await bus.publish("session_complete", {"session_id": "s1", "status": "completed"})
    await asyncio.sleep(0.05)

    assert len(l2.calls) == 1
    title, operations = l2.calls[0]
    assert title == "organize downloads"
    assert [op.operation for op in operations] == ["read_file_0", "read_file_1", "read_file_2"]
    await events.close()


@pytest.mark.asyncio
async def test_l2_skips_without_event_store(tmp_path):
    store = _make_store(tmp_path)

    class _FakeL2:
        called = False

        async def distill(self, *args: Any, **kwargs: Any) -> None:
            self.called = True

    l2 = _FakeL2()
    bus = EventBus()
    wire_self_learning(_FakeL1(), l2, store, bus, event_store=None)
    await bus.publish("session_complete", {"session_id": "s1"})
    await asyncio.sleep(0.05)

    assert l2.called is False


def test_default_embed_fn_produces_real_vectors():
    from app.core.long_context.embeddings import default_embed_fn

    embed = default_embed_fn()
    first = embed("hello world")
    second = embed("completely different sentence")

    assert len(first) == 384
    assert len(first) == len(second)
    assert first != second


@pytest.mark.asyncio
async def test_arch_v2_long_context_wires_real_rag(monkeypatch, tmp_path):
    from app import main

    monkeypatch.setattr(main.settings, "enable_arch_v2", True)
    monkeypatch.setattr(main.settings, "enable_long_context", True)
    monkeypatch.setattr(main.settings, "log_dir", str(tmp_path))
    monkeypatch.setattr(main, "BASE_DIR", tmp_path)

    handles = await main._init_arch_v2()
    assert handles is not None
    rag = handles.get("rag_index")
    assert rag is not None
    assert rag._embed is not None
    rag.close()
