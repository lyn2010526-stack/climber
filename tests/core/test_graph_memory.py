"""Graph memory reachability: opt-in gate, bounded extraction, bounded read.

Covers:
- default / missing / false ``memory_config`` resolves to disabled and the
  disabled producer performs no database work at all
- enabled extraction persists triples capped by ``max_triples_per_turn``
- a config asking for an absurd budget is clamped to the hard cap
- extraction and write failures never raise into the request path
- the read path works after extraction, stays bounded, and returns [] cheaply
  while the table is empty
- agent scoping follows the ``agent_id or None`` convention and one agent's
  triples never reach another agent's read
- the deterministic extractor: what it does capture, and that it stays quiet on
  prose with no known relation

Seeds real agents rows where an agent id is involved, because
``episodic_memories.agent_id`` is a foreign key to ``agents.id`` and SQLite runs
with ``PRAGMA foreign_keys=ON``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.persistent_memory import (
    GRAPH_MEMORY_DEFAULT_TRIPLES,
    GRAPH_MEMORY_HARD_TRIPLE_CAP,
    GRAPH_QUERY_HARD_LIMIT,
    GRAPH_SCOPE_SHARED,
    extract_triples,
    graph_scope_tag,
    persistent_memory,
    resolve_graph_memory_settings,
)
from app.storage.models_memory import KnowledgeGraph

RICH_CONTENT = (
    "User: My name is Alice and I work at Acme Corp.\n"
    "Assistant: The gateway runs on Kubernetes. Climber uses SQLAlchemy."
)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _ensure_agents(*agent_ids: str, user_id: str) -> None:
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

    async def _inner() -> None:
        async with async_session() as db:
            await db.execute(
                delete(KnowledgeGraph).where(KnowledgeGraph.user_id == user_id)
            )
            await db.commit()

    _run(_inner())


def _triples(user_id: str) -> list[KnowledgeGraph]:
    return _run(persistent_memory.query_graph(user_id, limit=GRAPH_QUERY_HARD_LIMIT))


def _enabled(max_triples: int | None = None) -> dict[str, Any]:
    config: dict[str, Any] = {"enabled": True}
    if max_triples is not None:
        config["max_triples_per_turn"] = max_triples
    return {"graph_memory": config}


# ─── Opt-in flag resolution ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "memory_config",
    [
        None,
        {},
        {"other_feature": {"enabled": True}},
        {"graph_memory": None},
        {"graph_memory": False},
        {"graph_memory": {"enabled": False}},
        {"graph_memory": {"enabled": False, "max_triples_per_turn": 5}},
        {"graph_memory": "yes"},
        {"graph_memory": 1},
        "not-a-dict",
    ],
)
def test_graph_memory_disabled_by_default(memory_config: Any) -> None:
    settings = resolve_graph_memory_settings(memory_config)
    assert settings.enabled is False
    assert settings.max_triples_per_turn == GRAPH_MEMORY_DEFAULT_TRIPLES


def test_bare_true_enables_with_default_budget() -> None:
    settings = resolve_graph_memory_settings({"graph_memory": True})
    assert settings.enabled is True
    assert settings.max_triples_per_turn == GRAPH_MEMORY_DEFAULT_TRIPLES


def test_enabled_budget_is_clamped_to_hard_cap() -> None:
    settings = resolve_graph_memory_settings(_enabled(max_triples=10_000))
    assert settings.enabled is True
    assert settings.max_triples_per_turn == GRAPH_MEMORY_HARD_TRIPLE_CAP


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(0, 1), (-4, 1), ("6", 6), (2.9, 2), ("not-a-number", GRAPH_MEMORY_DEFAULT_TRIPLES)],
)
def test_enabled_budget_normalization(requested: Any, expected: int) -> None:
    settings = resolve_graph_memory_settings(_enabled(max_triples=requested))
    assert settings.max_triples_per_turn == expected


# ─── Disabled path is a no-op ───────────────────────────────────────────────


def test_disabled_producer_performs_no_writes() -> None:
    user = "user-graph-off"
    try:
        stats = _run(persistent_memory.record_graph_memory(
            user_id=user, content=RICH_CONTENT, memory_config={}, agent_id=None,
        ))
        assert stats == {"enabled": 0, "extracted": 0, "stored": 0, "failed": 0}
        assert _triples(user) == []
    finally:
        _cleanup(user)


def test_disabled_producer_touches_no_session(monkeypatch: Any) -> None:
    """The gate must return before any DB session is opened."""
    import app.core.persistent_memory as pm

    opened: list[int] = []
    real_session = pm.async_session

    def _tracking_session(*args: Any, **kwargs: Any) -> Any:
        opened.append(1)
        return real_session(*args, **kwargs)

    monkeypatch.setattr(pm, "async_session", _tracking_session)
    for config in (None, {}, {"graph_memory": {"enabled": False}}, "not-a-dict"):
        stats = _run(pm.persistent_memory.record_graph_memory(
            user_id="user-graph-noio", content=RICH_CONTENT, memory_config=config,
        ))
        assert stats["stored"] == 0
    assert opened == []


def test_disabled_read_returns_nothing() -> None:
    assert _run(persistent_memory.query_agent_graph(
        user_id="user-graph-off-read",
        agent_id="agent-graph-off-read",
        memory_config={},
    )) == []
    assert _run(persistent_memory.format_graph_context_for_prompt(
        user_id="user-graph-off-read", memory_config={},
    )) == ""


# ─── Enabled extraction writes bounded triples ──────────────────────────────


def test_enabled_extracts_and_persists_triples() -> None:
    user = "user-graph-on"
    try:
        stats = _run(persistent_memory.record_graph_memory(
            user_id=user,
            content=RICH_CONTENT,
            memory_config=_enabled(max_triples=GRAPH_MEMORY_HARD_TRIPLE_CAP),
            agent_id=None,
        ))
        assert stats["enabled"] == 1
        assert stats["extracted"] >= 4
        assert stats["stored"] == stats["extracted"]
        assert stats["failed"] == 0

        rows = _triples(user)
        assert len(rows) == stats["stored"]
        pairs = {(r.subject, r.predicate, r.object_) for r in rows}
        assert ("user", "works_at", "acme corp") in pairs
        assert ("user", "named", "alice") in pairs
        assert ("gateway", "runs_on", "kubernetes") in pairs
        assert ("climber", "uses", "sqlalchemy") in pairs
    finally:
        _cleanup(user)


def test_default_budget_is_three_triples_per_turn() -> None:
    user = "user-graph-default-budget"
    try:
        stats = _run(persistent_memory.record_graph_memory(
            user_id=user, content=RICH_CONTENT, memory_config=_enabled(), agent_id=None,
        ))
        assert stats["stored"] == GRAPH_MEMORY_DEFAULT_TRIPLES
        assert len(_triples(user)) == GRAPH_MEMORY_DEFAULT_TRIPLES
    finally:
        _cleanup(user)


def test_per_turn_budget_is_respected() -> None:
    user = "user-graph-budget"
    try:
        stats = _run(persistent_memory.record_graph_memory(
            user_id=user,
            content=RICH_CONTENT,
            memory_config=_enabled(max_triples=1),
            agent_id=None,
        ))
        assert stats["stored"] == 1
        assert len(_triples(user)) == 1
    finally:
        _cleanup(user)


def test_huge_config_value_cannot_lift_the_hard_cap() -> None:
    """A misconfigured agent still writes at most GRAPH_MEMORY_HARD_TRIPLE_CAP rows."""
    user = "user-graph-huge"
    verbose = " ".join(
        f"Service{i} uses Library{i} and depends on Database{i}."
        for i in range(50)
    )
    try:
        stats = _run(persistent_memory.record_graph_memory(
            user_id=user,
            content=verbose,
            memory_config=_enabled(max_triples=999_999),
            agent_id=None,
        ))
        assert stats["extracted"] == GRAPH_MEMORY_HARD_TRIPLE_CAP
        assert stats["stored"] == GRAPH_MEMORY_HARD_TRIPLE_CAP
        assert len(_triples(user)) == GRAPH_MEMORY_HARD_TRIPLE_CAP
    finally:
        _cleanup(user)


def test_empty_content_stores_nothing() -> None:
    stats = _run(persistent_memory.record_graph_memory(
        user_id="user-graph-empty", content="   ", memory_config=_enabled(),
    ))
    assert stats["enabled"] == 1
    assert stats["extracted"] == 0
    assert stats["stored"] == 0


def test_extraction_never_raises_on_hostile_input() -> None:
    for content in ("", "\x00\x01", "a" * 5000, "i work at " + "x" * 300, "\n\n\n"):
        triples = extract_triples(content, GRAPH_MEMORY_HARD_TRIPLE_CAP)
        assert len(triples) <= GRAPH_MEMORY_HARD_TRIPLE_CAP


# ─── Failure containment ────────────────────────────────────────────────────


def test_extraction_failure_is_swallowed(monkeypatch: Any) -> None:
    import app.core.persistent_memory as pm

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("extractor exploded")

    monkeypatch.setattr(pm, "extract_triples", _boom)
    stats = _run(pm.persistent_memory.record_graph_memory(
        user_id="user-graph-boom", content=RICH_CONTENT, memory_config=_enabled(),
    ))
    assert stats["enabled"] == 1
    assert stats["stored"] == 0


def test_write_failure_is_counted_not_raised(monkeypatch: Any) -> None:
    import app.core.persistent_memory as pm

    async def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("db is down")

    monkeypatch.setattr(pm.persistent_memory, "add_triple", _boom)
    stats = _run(pm.persistent_memory.record_graph_memory(
        user_id="user-graph-wfail", content=RICH_CONTENT, memory_config=_enabled(),
    ))
    assert stats["extracted"] >= 1
    assert stats["stored"] == 0
    assert stats["failed"] == stats["extracted"]


def test_query_failure_returns_empty_list(monkeypatch: Any) -> None:
    import app.core.persistent_memory as pm

    real_session = pm.async_session

    def _broken_session(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("no database")

    monkeypatch.setattr(pm, "async_session", _broken_session)
    assert _run(pm.persistent_memory.query_agent_graph(
        user_id="user-graph-qfail",
        agent_id=None,
        memory_config=_enabled(),
    )) == []
    assert _run(pm.persistent_memory.format_graph_context_for_prompt(
        user_id="user-graph-qfail", memory_config=_enabled(),
    )) == ""
    monkeypatch.setattr(pm, "async_session", real_session)


# ─── Bounded read path ──────────────────────────────────────────────────────


def test_query_works_after_extraction_and_is_bounded() -> None:
    user = "user-graph-read"
    try:
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content=" ".join(f"Service{i} uses Library{i}." for i in range(30)),
            memory_config=_enabled(max_triples=12),
            agent_id=None,
        ))
        assert len(_triples(user)) == GRAPH_MEMORY_HARD_TRIPLE_CAP

        for requested, expected in ((2, 2), (5, 5), (GRAPH_QUERY_HARD_LIMIT, GRAPH_MEMORY_HARD_TRIPLE_CAP)):
            rows = _run(persistent_memory.query_graph(user, limit=requested))
            assert len(rows) == min(requested, GRAPH_MEMORY_HARD_TRIPLE_CAP) == expected

        # An absurd read budget is clamped to the hard maximum.
        rows = _run(persistent_memory.query_graph(user, limit=10_000))
        assert len(rows) == GRAPH_MEMORY_HARD_TRIPLE_CAP

        # Ordering is by confidence, which is stable for equal confidences.
        rows = _run(persistent_memory.query_graph(user, limit=GRAPH_QUERY_HARD_LIMIT))
        assert [r.confidence for r in rows] == sorted(
            (r.confidence for r in rows), reverse=True
        )
    finally:
        _cleanup(user)


def test_query_handles_empty_table_cheaply() -> None:
    user = "user-graph-empty-table"
    _cleanup(user)
    assert _run(persistent_memory.query_graph(user, limit=10)) == []
    assert _run(persistent_memory.query_agent_graph(
        user_id=user, agent_id=None, memory_config=_enabled(),
    )) == []
    assert _run(persistent_memory.format_graph_context_for_prompt(
        user_id=user, memory_config=_enabled(),
    )) == ""


def test_zero_limit_reads_nothing() -> None:
    assert _run(persistent_memory.query_graph("user-graph-zero", limit=0)) == []
    assert _run(persistent_memory.get_entity_relations("user-graph-zero", "x", limit=0)) == []


def test_agent_scoped_read_is_bounded() -> None:
    user = "user-graph-scoped-read"
    _ensure_agents("agent-graph-read", user_id=user)
    try:
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content=" ".join(f"Service{i} uses Library{i}." for i in range(30)),
            memory_config=_enabled(max_triples=12),
            agent_id="agent-graph-read",
        ))
        rows = _run(persistent_memory.query_agent_graph(
            user_id=user,
            agent_id="agent-graph-read",
            memory_config=_enabled(),
            limit=3,
        ))
        assert len(rows) == 3
        assert all("agent:agent-graph-read" in (r.tags or []) for r in rows)
    finally:
        _cleanup(user)


# ─── Agent scoping ──────────────────────────────────────────────────────────


def test_scope_tag_follows_agent_id_or_none_convention() -> None:
    assert graph_scope_tag(None) == GRAPH_SCOPE_SHARED
    assert graph_scope_tag("agent-1") == "agent:agent-1"


def test_shared_scope_is_used_when_agent_id_is_none() -> None:
    user = "user-graph-shared"
    try:
        _run(persistent_memory.record_graph_memory(
            user_id=user, content=RICH_CONTENT, memory_config=_enabled(), agent_id=None,
        ))
        rows = _triples(user)
        assert rows
        assert all(GRAPH_SCOPE_SHARED in (r.tags or []) for r in rows)
    finally:
        _cleanup(user)


def test_other_agents_triples_do_not_leak() -> None:
    user = "user-graph-isolation"
    _ensure_agents("agent-graph-a", "agent-graph-b", user_id=user)
    try:
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content="Alice works at Acme Corp.",
            memory_config=_enabled(),
            agent_id="agent-graph-a",
        ))
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content="Alice works at Globex Inc.",
            memory_config=_enabled(),
            agent_id="agent-graph-b",
        ))
        # Same subject+predicate, different object and different scope: both rows survive.
        assert len(_triples(user)) == 2

        rows_a = _run(persistent_memory.query_agent_graph(
            user_id=user, agent_id="agent-graph-a", memory_config=_enabled(),
        ))
        rows_b = _run(persistent_memory.query_agent_graph(
            user_id=user, agent_id="agent-graph-b", memory_config=_enabled(),
        ))
        objects_a = {r.object_ for r in rows_a}
        objects_b = {r.object_ for r in rows_b}
        assert objects_a == {"acme corp"}
        assert objects_b == {"globex inc"}

        # The shared pool (agent_id -> None) sees neither agent's triples.
        assert _run(persistent_memory.query_agent_graph(
            user_id=user, agent_id=None, memory_config=_enabled(),
        )) == []
    finally:
        _cleanup(user)


def test_repeat_write_merges_within_scope_only() -> None:
    user = "user-graph-merge"
    _ensure_agents("agent-graph-m1", "agent-graph-m2", user_id=user)
    try:
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content="The gateway runs on Kubernetes.",
            memory_config=_enabled(),
            agent_id="agent-graph-m1",
        ))
        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content="The gateway runs on Kubernetes.",
            memory_config=_enabled(),
            agent_id="agent-graph-m1",
        ))
        assert len(_triples(user)) == 1  # merged, confidence raised

        _run(persistent_memory.record_graph_memory(
            user_id=user,
            content="The gateway runs on Kubernetes.",
            memory_config=_enabled(),
            agent_id="agent-graph-m2",
        ))
        rows = _run(persistent_memory.query_agent_graph(
            user_id=user, agent_id="agent-graph-m2", memory_config=_enabled(),
        ))
        assert len(rows) == 1
        assert rows[0].tags == ["agent:agent-graph-m2"]
    finally:
        _cleanup(user)


def test_settings_resolved_from_agent_row(monkeypatch: Any) -> None:
    user = "user-graph-cfg"
    _ensure_agents("agent-graph-cfg", user_id=user)

    async def _disable(*args: Any, **kwargs: Any) -> None:
        from sqlalchemy import update

        from app.storage import async_session
        from app.storage.database import Agent

        async with async_session() as db:
            await db.execute(
                update(Agent).where(Agent.id == "agent-graph-cfg").values(memory_config={})
            )
            await db.commit()

    async def _enable(*args: Any, **kwargs: Any) -> None:
        from sqlalchemy import update

        from app.storage import async_session
        from app.storage.database import Agent

        async with async_session() as db:
            await db.execute(
                update(Agent)
                .where(Agent.id == "agent-graph-cfg")
                .values(memory_config=_enabled(max_triples=2))
            )
            await db.commit()

    try:
        _run(_enable())
        settings = _run(persistent_memory.get_graph_memory_settings("agent-graph-cfg"))
        assert settings.enabled is True
        assert settings.max_triples_per_turn == 2

        _run(_disable())
        assert _run(
            persistent_memory.get_graph_memory_settings("agent-graph-cfg")
        ).enabled is False
        # No agent id at all (shared pool) can never be opted in.
        assert _run(
            persistent_memory.get_graph_memory_settings(None)
        ).enabled is False
    finally:
        _cleanup(user)


# ─── Extractor behavior, including what it deliberately misses ──────────────


def test_extractor_is_deterministic() -> None:
    first = extract_triples(RICH_CONTENT, GRAPH_MEMORY_HARD_TRIPLE_CAP)
    second = extract_triples(RICH_CONTENT, GRAPH_MEMORY_HARD_TRIPLE_CAP)
    assert [(t.subject, t.predicate, t.object) for t in first] == [
        (t.subject, t.predicate, t.object) for t in second
    ]


def test_extractor_stays_quiet_on_unrelated_prose() -> None:
    assert extract_triples(
        "The weather is nice today and the cat sat on the mat.", 8
    ) == []


def test_extractor_honors_its_own_budget() -> None:
    verbose = " ".join(f"Service{i} uses Library{i}." for i in range(20))
    assert len(extract_triples(verbose, 4)) == 4
    assert extract_triples(verbose, 0) == []


def test_extractor_normalizes_and_bounds_entities() -> None:
    triples = extract_triples(
        "The very long deployment pipeline for the payments service uses terraform.",
        8,
    )
    assert len(triples) == 1
    triple = triples[0]
    assert triple.subject == "payments service"
    assert triple.object == "terraform"
    assert triple.predicate == "uses"
    assert triple.context


def test_extractor_stamps_low_confidence() -> None:
    triple = extract_triples("The gateway runs on Kubernetes.", 1)[0]
    assert triple.confidence < 0.8
