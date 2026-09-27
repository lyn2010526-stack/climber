"""Core-memory self-editing tools + Letta block-scope semantics.

Covers:
- core_memory_append / core_memory_replace builtin tools resolve their target
  user/agent from the server-side contextvar (app/core/memory_context), never
  from model-supplied arguments.
- read_only blocks are never mutated.
- Letta block visibility: an agent sees global blocks PLUS its own overrides;
  get_block prefers the agent block and falls back to the global one.

Runs with --noconftest (no DB fixture needed; we use the real async_session
against the test DB, seeding agents rows to satisfy the agent_id FK).
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core import core_memory as core_memory_module
from app.core.memory_context import clear_memory_scope, set_memory_scope
from app.tools.builtins import core_memory_append, core_memory_replace


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _ensure_agents(*agent_ids: str, user_id: str) -> None:
    """Insert real agents rows so CoreMemoryBlock.agent_id FK holds (SQLite FK on)."""
    from app.storage import async_session
    from app.storage.database import Agent

    async def _inner() -> None:
        async with async_session() as db:
            for agent_id in agent_ids:
                db.add(Agent(id=agent_id, user_id=user_id, name=agent_id, provider="openai", model_id="gpt-4o"))
            await db.commit()

    _run(_inner())


def _cleanup(user_id: str) -> None:
    from sqlalchemy import delete

    from app.storage import async_session
    from app.storage.models_memory import CoreMemoryBlock

    async def _inner() -> None:
        async with async_session() as db:
            await db.execute(delete(CoreMemoryBlock).where(CoreMemoryBlock.user_id == user_id))
            await db.commit()

    _run(_inner())


# ─── Self-editing tools: scope from context, never from arguments ───────────


def test_append_uses_server_side_scope(monkeypatch: Any) -> None:
    _ensure_agents("agent-cm-1", user_id="user-cm")
    set_memory_scope("user-cm", "agent-cm-1")
    try:
        out = _run(core_memory_append(label="persona", text="friendly helper"))
        assert "Appended" in out
        blocks = _run(core_memory_module.core_memory.get_blocks("user-cm", agent_id="agent-cm-1"))
        assert any(b.label == "persona" and "friendly helper" in b.value for b in blocks)
        # block is agent-scoped, not global
        assert any(b.agent_id == "agent-cm-1" for b in blocks)
    finally:
        clear_memory_scope()
        _cleanup("user-cm")


def test_append_without_scope_refuses_to_write() -> None:
    clear_memory_scope()
    out = _run(core_memory_append(label="persona", text="x"))
    assert "no active user memory scope" in out


def test_append_never_writes_other_users_memory() -> None:
    _ensure_agents("agent-other", user_id="victim")
    set_memory_scope("attacker", "agent-other")
    try:
        _run(core_memory_append(label="persona", text="injected"))
        blocks = _run(core_memory_module.core_memory.get_blocks("victim"))
        # attacker scoped write must not land in victim's pool
        assert all("injected" not in b.value for b in blocks)
    finally:
        clear_memory_scope()
        _cleanup("attacker")
        _cleanup("victim")


def test_read_only_block_not_mutated() -> None:
    _ensure_agents("agent-ro", user_id="user-ro")
    set_memory_scope("user-ro", "agent-ro")
    try:
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-ro", "system", "LOCKED", agent_id="agent-ro", read_only=True
        ))
        out = _run(core_memory_append(label="system", text="SHOULD NOT STICK"))
        assert "read-only" in out.lower()
        block = _run(core_memory_module.core_memory.get_block("user-ro", "system", agent_id="agent-ro"))
        assert block.value == "LOCKED"
    finally:
        clear_memory_scope()
        _cleanup("user-ro")


def test_replace_updates_block() -> None:
    _ensure_agents("agent-rep", user_id="user-rep")
    set_memory_scope("user-rep", "agent-rep")
    try:
        _run(core_memory_append(label="project", text="uses mysql"))
        out = _run(core_memory_replace(label="project", old_text="mysql", new_text="postgres"))
        assert "Updated" in out
        block = _run(core_memory_module.core_memory.get_block("user-rep", "project", agent_id="agent-rep"))
        assert "postgres" in block.value
        assert "mysql" not in block.value
    finally:
        clear_memory_scope()
        _cleanup("user-rep")


def test_replace_missing_block_reports_error() -> None:
    _ensure_agents("agent-rep2", user_id="user-rep2")
    set_memory_scope("user-rep2", "agent-rep2")
    try:
        out = _run(core_memory_replace(label="ghost", old_text="a", new_text="b"))
        assert "not found" in out
    finally:
        clear_memory_scope()
        _cleanup("user-rep2")


# ─── Letta block visibility: agent sees global + own override ────────────────


def test_agent_sees_global_and_own_blocks() -> None:
    _ensure_agents("agent-vis", user_id="user-vis")
    try:
        # global persona (no agent_id) + agent-specific note
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-vis", "persona", "GLOBAL PERSONA", agent_id=None
        ))
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-vis", "project", "AGENT PROJECT", agent_id="agent-vis"
        ))
        blocks = _run(core_memory_module.core_memory.get_blocks("user-vis", agent_id="agent-vis"))
        labels = {b.label for b in blocks}
        assert "persona" in labels  # global visible to the agent
        assert "project" in labels  # own block visible
    finally:
        _cleanup("user-vis")


def test_agent_override_hides_duplicate_global_label() -> None:
    _ensure_agents("agent-override", user_id="user-override")
    try:
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-override", "persona", "GLOBAL", agent_id=None
        ))
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-override", "persona", "AGENT", agent_id="agent-override"
        ))

        blocks = _run(core_memory_module.core_memory.get_blocks("user-override", agent_id="agent-override"))

        assert [(block.label, block.value) for block in blocks].count(("persona", "AGENT")) == 1
        assert all(block.value != "GLOBAL" for block in blocks)
    finally:
        _cleanup("user-override")


def test_core_memory_rejects_invalid_block_limits() -> None:
    try:
        _run(core_memory_module.core_memory.create_or_update_block("user-invalid", "", "value"))
    except ValueError:
        pass
    else:
        raise AssertionError("empty labels must be rejected")


def test_get_block_prefers_agent_override_then_global() -> None:
    _ensure_agents("agent-pref", user_id="user-pref")
    try:
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-pref", "persona", "GLOBAL", agent_id=None
        ))
        # before override exists, agent resolves the global block
        first = _run(core_memory_module.core_memory.get_block("user-pref", "persona", agent_id="agent-pref"))
        assert first is not None and first.value == "GLOBAL"
        # create agent override
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-pref", "persona", "AGENT OVERRIDE", agent_id="agent-pref"
        ))
        second = _run(core_memory_module.core_memory.get_block("user-pref", "persona", agent_id="agent-pref"))
        assert second is not None and second.value == "AGENT OVERRIDE"
    finally:
        _cleanup("user-pref")


def test_global_pool_default_unchanged_when_no_agent() -> None:
    """Backward compat: get_blocks without agent_id returns only global blocks."""
    _ensure_agents("agent-gdef", user_id="user-gdef")
    try:
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-gdef", "persona", "GLOBAL", agent_id=None
        ))
        _run(core_memory_module.core_memory.create_or_update_block(
            "user-gdef", "secret", "AGENT ONLY", agent_id="agent-gdef"
        ))
        blocks = _run(core_memory_module.core_memory.get_blocks("user-gdef"))  # no agent_id
        labels = {b.label for b in blocks}
        assert "persona" in labels
        assert "secret" not in labels  # agent-specific not leaked into global view
    finally:
        _cleanup("user-gdef")
