"""Memory-scope wiring tests (research-100 P2a follow-up).

P2a added mem0-style ``agent_id`` scoping to ``retrieve_memories``, but the
production injection path never forwarded it, so the scope was unreachable.
These tests pin the wiring: ``_inject_memory_context`` must forward the
session's agent scope, and an empty agent id must fall back to the shared pool.
"""

from __future__ import annotations

from typing import Any

from app.core.agent_engine import AgentEngine


class _RecordingMemory:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def format_memories_for_prompt(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return ""


def _engine_with(memory: Any) -> AgentEngine:
    engine = AgentEngine(model_registry=object(), tool_registry=object())
    engine.memory_service = memory
    return engine


def _session(engine: AgentEngine, agent_id: str):
    return engine.create_session(
        agent_id=agent_id,
        user_id="u",
        provider="openai",
        model_id="gpt-4o-mini",
        api_key="",
        session_id="s-mem",
        tools=[],
    )


async def test_injection_forwards_agent_scope() -> None:
    memory = _RecordingMemory()
    engine = _engine_with(memory)
    session = _session(engine, "agent-77")

    await engine._inject_memory_context(session, "hello")

    assert memory.calls, "memory service was never queried"
    assert memory.calls[-1]["agent_id"] == "agent-77"


async def test_empty_agent_id_falls_back_to_shared_pool() -> None:
    memory = _RecordingMemory()
    engine = _engine_with(memory)
    session = _session(engine, "")

    await engine._inject_memory_context(session, "hello")

    assert memory.calls[-1]["agent_id"] is None


async def test_injection_still_returns_memory_context_when_present() -> None:
    class _Memory:
        async def format_memories_for_prompt(self, **kwargs: Any) -> str:
            return "## Relevant Memories:\n- [note] a fact"

    engine = _engine_with(_Memory())
    session = _session(engine, "agent-1")

    await engine._inject_memory_context(session, "hello")

    injected = [m for m in session.messages if str(m.get("content", "")).startswith("<!-- MEMORY_CONTEXT -->")]
    assert injected and "a fact" in injected[-1]["content"]


async def test_injection_reads_none_agent_id_without_crashing() -> None:
    memory = _RecordingMemory()
    engine = _engine_with(memory)
    session = _session(engine, None)  # type: ignore[arg-type]

    await engine._inject_memory_context(session, "hello")

    assert memory.calls[-1]["agent_id"] is None
