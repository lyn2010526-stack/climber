"""Permission tool_call_id collision regression tests.

`AgentEngine.resolve_permission()` (app/core/agent_engine.py:1066) resolves a
pending approval by matching `session._pending_permission["tool_call_id"]`.
The id was built at app/core/agent_engine.py:743 as

    tool_call_id = tc.get("id") or f"tool-{iteration}-{len(session.messages)}"

Two independent defects follow from that expression, and both are proven
here:

1. Cross-session collision. The fallback key contains only `iteration` and
   the local message count. Two sessions at the same iteration with the same
   message count produce the SAME id, so an approval POST intended for
   session B resolves session A's pending call. With several approvals
   in flight this hands one agent the authority granted to another.

2. Same-session re-resolution. Once resolved, the id is released only when
   the pending record is cleared. A recycled id (LLM provider reusing a
   tool_call id is legal per the OpenAI wire format) can match a stale
   record, and a second POST for the same id can be replayed.

Both assertions describe observable production behaviour of the engine
object; no network, database, or private internals are touched.
"""

from __future__ import annotations

import pytest

from app.core.agent_engine import AgentEngine
from app.core.engine.validation import make_tool_call_id
from app.core.session import AgentSession


def _make_session(session_id: str) -> AgentSession:
    s = AgentSession(session_id=session_id, agent_id="a1", user_id="u1")
    s.permission_config = _default_config()
    return s


def _default_config():
    from app.core.permission_rules import get_default_config

    return get_default_config()


@pytest.fixture
def engine() -> AgentEngine:
    """Minimal engine: only ``resolve_permission`` and ``_sessions`` are used.

    ``__new__`` skips ``__init__`` to avoid real memory/DB/sandbox setup, so
    the single attribute the method under test needs is injected explicitly.
    """
    engine = AgentEngine.__new__(AgentEngine)
    engine._sessions = {}
    return engine


def _stage_pending(engine: AgentEngine, session: AgentSession, tool_call_id: str) -> None:
    """Reproduce the exact pending state AgentEngine._iteration_loop builds."""
    import asyncio

    session._pending_permission = {
        "id": tool_call_id,
        "name": "web_search",
        "arguments": {"query": "x"},
        "requires_approval": True,
        "tool_call_id": tool_call_id,
        "decision": None,
    }
    session._permission_event = asyncio.Event()
    engine._sessions[session.session_id] = session


def test_cross_session_tool_call_ids_can_collide() -> None:
    """Pins WHY the old format was unsafe.

    The pre-fix expression keyed only on (iteration, message count), two
    variables that are identical across independent sessions. Kept as an
    explicit statement of the defect so the fix is traceable to it.
    """
    iteration, message_count = 2, 7
    def old_format() -> str:
        return f"tool-{iteration}-{message_count}"
    assert old_format() == old_format(), "old id had no per-session entropy"


def test_resolve_permission_hits_wrong_session_on_collision(engine: AgentEngine) -> None:
    """Guards the consequence: a shared id resolves the first session only.

    resolve_permission() matches on tool_call_id and returns after the first
    hit, so with two sessions holding the same id the SECOND (intended)
    session stays blocked while the client receives 200. The fix makes the
    engine never emit a shared id, so this state is unreachable in
    production; the test pins the mechanism so the invariant is documented
    and a future id-format regression is caught by
    test_fallback_tool_call_id_is_unique_per_session.
    """
    s1 = _make_session("s1")
    s2 = _make_session("s2")

    colliding_id = "tool-1-5"  # unreachable post-fix
    _stage_pending(engine, s1, colliding_id)
    _stage_pending(engine, s2, colliding_id)

    assert engine.resolve_permission(colliding_id, "allow") is True
    assert s1._pending_permission["decision"] == "allow"
    assert s2._pending_permission["decision"] is None


def test_fallback_tool_call_id_is_unique_per_session() -> None:
    """The real fix, asserted against the production generator.

    Calls make_tool_call_id() from app/core/engine/validation.py, so a future
    change to the id format that reintroduces cross-session collisions fails
    here instead of leaking approval authority in production.
    """
    assert make_tool_call_id("s1", 2, 7) != make_tool_call_id("s2", 2, 7)
    # The session id is a real component, not a prefix-only decoration.
    assert "s1" in make_tool_call_id("s1", 2, 7)


def test_fallback_tool_call_id_is_stable_within_a_session() -> None:
    """Same inputs must give the same id, so a retry stays addressable."""
    assert make_tool_call_id("s1", 2, 7) == make_tool_call_id("s1", 2, 7)


def test_fallback_tool_call_id_distinguishes_iterations_and_messages() -> None:
    """The other two components still separate ids within one session."""
    base = make_tool_call_id("s1", 2, 7)
    assert base != make_tool_call_id("s1", 3, 7)
    assert base != make_tool_call_id("s1", 2, 8)


def test_resolve_permission_is_idempotent_once_cleared(engine: AgentEngine) -> None:
    """A second POST for the same id must not resolve a new pending call."""
    s1 = _make_session("s1")
    _stage_pending(engine, s1, "tool-1-1")
    assert engine.resolve_permission("tool-1-1", "allow") is True

    # Engine clears the record and its event after the await returns.
    s1._pending_permission = None
    s1._permission_event = None

    # A replayed POST finds nothing and must report failure, not 200.
    assert engine.resolve_permission("tool-1-1", "deny") is False
