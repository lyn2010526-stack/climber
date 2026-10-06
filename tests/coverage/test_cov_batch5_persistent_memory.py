"""Coverage tests for app/core/persistent_memory.py.

Uses a per-test in-memory SQLite engine (StaticPool) instead of the shared
test DB so the tests are order-independent and immune to connection-pool /
event-loop reuse across tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.core.persistent_memory as pm_module
from app.core.persistent_memory import PersistentMemoryService
from app.storage import Base
from app.storage.models_memory import (
    ArchivalPassage,
    EpisodicMemory,
    MemoryRetrievalLog,
    UserProfile,
)


class FakeVector:
    """In-memory stand-in for app.core.vector_memory.vector_memory."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, str]] = {}
        self.added: list[tuple[str, str, str, dict[str, Any]]] = []
        self.access_updates: list[tuple[str, str]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.fail_add = False
        self.fail_search = False
        self.search_results: list[dict[str, Any]] | None = None

    async def add(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if self.fail_add:
            raise RuntimeError("vector add failed")
        self.added.append((collection, str(doc_id), text, metadata or {}))
        self.records.setdefault(collection, {})[str(doc_id)] = text
        return str(doc_id)

    async def search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        profile_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        self.search_calls.append({"collection": collection, "query": query, "top_k": top_k})
        if self.fail_search:
            raise RuntimeError("vector search failed")
        if self.search_results is not None:
            return self.search_results[:top_k]
        out = [
            {"id": doc_id, "text": text}
            for doc_id, text in self.records.get(collection, {}).items()
        ]
        return out[:top_k]

    async def update_access(self, collection: str, doc_id: str) -> None:
        self.access_updates.append((collection, str(doc_id)))


@pytest_asyncio.fixture
async def env(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    fake = FakeVector()
    monkeypatch.setattr(pm_module, "async_session", maker)
    monkeypatch.setattr(pm_module, "vector_memory", fake)
    env = SimpleNamespace(svc=PersistentMemoryService(), fake=fake, maker=maker)
    yield env
    await engine.dispose()


async def _get_memory(env, memory_id: str) -> EpisodicMemory | None:
    async with env.maker() as db:
        return (
            await db.execute(select(EpisodicMemory).where(EpisodicMemory.id == memory_id))
        ).scalar_one_or_none()


# ── episodic ──────────────────────────────────────────────────────────────


async def test_create_episodic_memory(env) -> None:
    mem = await env.svc.create_episodic_memory(
        user_id="pm-create",
        content="A long conversation summary that should be stored",
        agent_id=None,
        memory_type="decision",
        importance=0.7,
        tags=["t1"],
        source_session_id="sess-1",
        metadata={"k": "v"},
    )
    assert mem.user_id == "pm-create"
    assert mem.summary == "A long conversation summary that should be stored"[:200]
    assert mem.tags == ["t1"]
    assert mem.metadata_ == {"k": "v"}
    assert any(c == "episodic" and did == mem.id for c, did, _, _ in env.fake.added)


async def test_create_episodic_memory_vector_failure(env) -> None:
    env.fake.fail_add = True
    mem = await env.svc.create_episodic_memory(user_id="pm-create-fail", content="content here")
    assert mem.id


async def test_retrieve_memories_vector_hits(env) -> None:
    a = await env.svc.create_episodic_memory(user_id="pm-vec", content="alpha memory content")
    b = await env.svc.create_episodic_memory(user_id="pm-vec", content="beta memory content")
    env.fake.search_results = [{"id": a.id}, {"id": b.id}]

    results = await env.svc.retrieve_memories("pm-vec", query="memory", limit=5, session_id="s")
    assert [m.id for m in results] == [a.id, b.id]
    async with env.maker() as db:
        logs = (await db.execute(select(MemoryRetrievalLog))).scalars().all()
    assert len(logs) == 2
    reloaded = await _get_memory(env, a.id)
    assert reloaded.access_count == 1
    assert reloaded.last_accessed_at is not None


async def test_retrieve_memories_vector_filtered_falls_back_to_keyword(env) -> None:
    mem = await env.svc.create_episodic_memory(
        user_id="pm-fallback", content="gateway routing on port 9000", importance=0.6
    )
    # Vector returns an id that does not exist in the DB -> ordered empty -> keyword path
    env.fake.search_results = [{"id": "does-not-exist"}]
    results = await env.svc.retrieve_memories("pm-fallback", query="gateway routing")
    assert [m.id for m in results] == [mem.id]


async def test_retrieve_memories_vector_search_raises(env) -> None:
    mem = await env.svc.create_episodic_memory(user_id="pm-vecerr", content="unique token zebra")
    env.fake.fail_search = True
    results = await env.svc.retrieve_memories("pm-vecerr", query="zebra")
    assert [m.id for m in results] == [mem.id]


async def test_retrieve_memories_no_query_and_short_keywords(env) -> None:
    a = await env.svc.create_episodic_memory(user_id="pm-noq", content="first", importance=0.9)
    b = await env.svc.create_episodic_memory(user_id="pm-noq", content="second", importance=0.2)

    ordered = await env.svc.retrieve_memories("pm-noq", limit=10)
    assert [m.id for m in ordered] == [a.id, b.id]

    # all tokens <= 3 chars -> no keyword expansion, still returns rows
    env.fake.search_results = []  # force the keyword fallback path
    short = await env.svc.retrieve_memories("pm-noq", query="a b c", limit=10)
    assert {m.id for m in short} == {a.id, b.id}


async def test_retrieve_memories_keyword_boost_increments_access(env) -> None:
    mem = await env.svc.create_episodic_memory(
        user_id="pm-boost", content="python concurrency patterns", importance=0.5
    )
    results = await env.svc.retrieve_memories("pm-boost", query="concurrency", limit=5)
    assert [m.id for m in results] == [mem.id]
    reloaded = await _get_memory(env, mem.id)
    assert reloaded.access_count == 1


async def test_retrieve_memories_no_keyword_match(env) -> None:
    mem = await env.svc.create_episodic_memory(
        user_id="pm-nomatch", content="python concurrency patterns", importance=0.5
    )
    env.fake.search_results = []  # force the keyword fallback path
    # non-empty keyword list, but the token appears nowhere -> any(...) false
    results = await env.svc.retrieve_memories("pm-nomatch", query="zzzznotpresent")
    assert [m.id for m in results] == [mem.id]
    reloaded = await _get_memory(env, mem.id)
    assert reloaded.access_count == 0


async def test_format_memories_for_prompt(env) -> None:
    assert await env.svc.format_memories_for_prompt("pm-empty") == ""
    await env.svc.create_episodic_memory(
        user_id="pm-fmt", content="remember the milk", memory_type="preference"
    )
    text = await env.svc.format_memories_for_prompt("pm-fmt", query="milk")
    assert text.startswith("## Relevant Memories:")
    assert "[preference] remember the milk" in text


async def test_decay_recency_scores(env) -> None:
    await env.svc.create_episodic_memory(user_id="pm-decay", content="x")
    await env.svc.create_episodic_memory(user_id="pm-decay", content="y")
    count = await env.svc.decay_recency_scores(decay_factor=0.5)
    assert count == 2
    async with env.maker() as db:
        rows = (
            (await db.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == "pm-decay")))
            .scalars()
            .all()
        )
    assert all(m.recency_score == 0.5 for m in rows)


async def test_cleanup_old_memories(env) -> None:
    for i in range(3):
        await env.svc.create_episodic_memory(user_id="pm-clean", content=f"m{i}")

    assert await env.svc.cleanup_old_memories("pm-clean", keep_count=10) == 0

    async with env.maker() as db:
        rows = (
            (await db.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == "pm-clean")))
            .scalars()
            .all()
        )
        for m in rows:
            m.recency_score = 0.0
        await db.commit()

    deleted = await env.svc.cleanup_old_memories("pm-clean", keep_count=1, min_score=0.01)
    assert deleted == 2


async def test_auto_archive_old_memories(env) -> None:
    recent = await env.svc.create_episodic_memory(
        user_id="pm-archive", content="recent", importance=0.1
    )
    old = await env.svc.create_episodic_memory(
        user_id="pm-archive", content="old note", importance=0.1
    )
    async with env.maker() as db:
        row = await db.get(EpisodicMemory, old.id)
        row.created_at = datetime.now(UTC) - timedelta(days=90)
        await db.commit()

    stats = await env.svc.auto_archive_old_memories("pm-archive", max_episodic_age_days=30)
    assert stats == {"archived": 1, "skipped": 0, "failed": 0}
    assert await _get_memory(env, old.id) is None
    assert await _get_memory(env, recent.id) is not None
    async with env.maker() as db:
        passages = (
            (
                await db.execute(
                    select(ArchivalPassage).where(ArchivalPassage.user_id == "pm-archive")
                )
            )
            .scalars()
            .all()
        )
    assert len(passages) == 1


async def test_auto_archive_failure(env, monkeypatch) -> None:
    old = await env.svc.create_episodic_memory(user_id="pm-afail", content="old", importance=0.1)
    async with env.maker() as db:
        row = await db.get(EpisodicMemory, old.id)
        row.created_at = datetime.now(UTC) - timedelta(days=90)
        await db.commit()

    async def boom(**kwargs):
        raise RuntimeError("archive failed")

    monkeypatch.setattr(env.svc, "create_archival_passage", boom)
    stats = await env.svc.auto_archive_old_memories("pm-afail", max_episodic_age_days=30)
    assert stats["failed"] == 1
    assert stats["archived"] == 0


# ── knowledge graph ───────────────────────────────────────────────────────


async def test_add_triple_new_and_existing(env) -> None:
    triple = await env.svc.add_triple("pm-kg", "Alice", "works_at", "Acme", confidence=0.5)
    assert triple.subject == "Alice"

    again = await env.svc.add_triple("pm-kg", "Alice", "works_at", "Acme", confidence=0.9)
    assert again.id == triple.id
    assert again.confidence == 0.9

    lower = await env.svc.add_triple("pm-kg", "Alice", "works_at", "Acme", confidence=0.1)
    assert lower.confidence == 0.9  # max() preserved


async def test_query_graph_and_relations(env) -> None:
    await env.svc.add_triple("pm-kg2", "Bob", "likes", "Tea", confidence=0.7)
    await env.svc.add_triple("pm-kg2", "Bob", "knows", "Python", confidence=0.9)
    await env.svc.add_triple("pm-kg2", "Carol", "likes", "Coffee", confidence=0.6)

    all_rows = await env.svc.query_graph("pm-kg2")
    assert len(all_rows) == 3
    assert all_rows[0].confidence == 0.9  # ordered by confidence desc

    assert len(await env.svc.query_graph("pm-kg2", subject="Bob")) == 2
    assert len(await env.svc.query_graph("pm-kg2", predicate="likes")) == 2
    assert len(await env.svc.query_graph("pm-kg2", object_="Tea")) == 1

    relations = await env.svc.get_entity_relations("pm-kg2", "Bob", limit=1)
    assert len(relations) == 1
    assert relations[0].subject == "Bob"


async def test_format_graph_for_prompt(env) -> None:
    assert await env.svc.format_graph_for_prompt("pm-kg3", "Nobody") == ""
    await env.svc.add_triple("pm-kg3", "Dan", "uses", "Vim")
    text = await env.svc.format_graph_for_prompt("pm-kg3", "Dan")
    assert text.startswith('## Knowledge about "Dan":')
    assert "Dan -[uses]-> Vim" in text


# ── user profile ──────────────────────────────────────────────────────────


async def test_get_or_create_profile(env) -> None:
    created = await env.svc.get_or_create_profile("pm-prof-1")
    assert created.id
    again = await env.svc.get_or_create_profile("pm-prof-1")
    assert again.id == created.id


async def test_add_user_fact_and_truncation(env) -> None:
    profile = await env.svc.add_user_fact("pm-prof-2", "likes tea", "food", 0.9)
    assert profile.facts[-1]["content"] == "likes tea"
    assert profile.facts[-1]["category"] == "food"

    for i in range(105):
        profile = await env.svc.add_user_fact("pm-prof-3", f"fact-{i}")
    assert len(profile.facts) == 100
    assert profile.facts[-1]["content"] == "fact-104"


async def test_update_preferences(env) -> None:
    updated = await env.svc.update_preferences(
        "pm-prof-4",
        preferred_model="gpt-4o",
        preferred_language="fr",
        not_a_field="ignored",
        timezone=None,
    )
    assert updated.preferred_model == "gpt-4o"
    assert updated.preferred_language == "fr"


async def test_record_interaction(env) -> None:
    await env.svc.record_interaction("pm-prof-5", message_count=3)
    async with env.maker() as db:
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == "pm-prof-5"))
        ).scalar_one()
    assert profile.total_sessions == 1
    assert profile.total_messages == 3
    assert profile.first_interaction is not None
    first = profile.first_interaction

    await env.svc.record_interaction("pm-prof-5")
    async with env.maker() as db:
        profile2 = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == "pm-prof-5"))
        ).scalar_one()
    assert profile2.total_sessions == 2
    assert profile2.first_interaction == first


async def test_format_profile_for_prompt(env) -> None:
    # A freshly created profile still has the model default language; blank it
    # so the "nothing to inject" branch is exercised.
    empty_profile = await env.svc.get_or_create_profile("pm-prof-empty")
    async with env.maker() as db:
        row = await db.get(UserProfile, empty_profile.id)
        row.preferred_language = ""
        await db.commit()
    assert await env.svc.format_profile_for_prompt("pm-prof-empty") == ""

    await env.svc.add_user_fact("pm-prof-6", "works at Acme", "work")
    async with env.maker() as db:
        profile = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == "pm-prof-6"))
        ).scalar_one()
        profile.inviolable = ["never lie"]
        profile.values = ["honesty"]
        profile.principles = ["be kind"]
        profile.preferred_model = "gpt-4o"
        profile.preferred_language = "en"
        await db.merge(profile)
        await db.commit()

    text = await env.svc.format_profile_for_prompt("pm-prof-6")
    assert "[INVIOLABLE RULES" in text
    assert "never lie" in text
    assert "## User Values" in text
    assert "## User Principles" in text
    assert "## User Information:" in text
    assert "Preferred model: gpt-4o" in text
    assert "Preferred language: en" in text


# ── auto extraction ───────────────────────────────────────────────────────


async def test_auto_extract_from_session(env) -> None:
    stats = await env.svc.auto_extract_from_session(
        user_id="pm-extract",
        session_id="sess-x",
        messages=[
            {"content": "short"},
            {"content": "I prefer dark mode in all my editors"},
            {"content": "My name is Alice Smith Jones Extra"},
            {"content": "I work at Acme Corp as an engineer"},
            {"content": "The weather is nice today and nothing else"},
        ],
    )
    assert stats["memories"] == 3
    assert stats["facts"] == 2
    assert stats["triples"] == 0

    async with env.maker() as db:
        facts_row = (
            await db.execute(select(UserProfile).where(UserProfile.user_id == "pm-extract"))
        ).scalar_one()
    contents = [f["content"] for f in facts_row.facts]
    assert any(c.startswith("Name: Alice") for c in contents)
    assert any(c.startswith("Work: at Acme") for c in contents)


async def test_auto_extract_empty_name_and_work(env) -> None:
    stats = await env.svc.auto_extract_from_session(
        user_id="pm-extract-empty",
        session_id="sess-y",
        messages=[
            {"content": "My name is !!!!!!!!!!!!!!!!!!!!!"},
            {"content": "I work                        "},
        ],
    )
    # memories are still created, but no facts because the extracted value is blank
    assert stats["memories"] == 2
    assert stats["facts"] == 0


# ── archival ──────────────────────────────────────────────────────────────


async def test_create_archival_passage_vector_failure(env) -> None:
    env.fake.fail_add = True
    passage = await env.svc.create_archival_passage(
        user_id="pm-arch-fail", text="body", archive_id="a1"
    )
    assert passage.id


async def test_search_archival_memories(env) -> None:
    p1 = await env.svc.create_archival_passage(
        user_id="pm-search", text="deployment playbook", archive_id="a1", tags=["ops", "deploy"]
    )
    p2 = await env.svc.create_archival_passage(
        user_id="pm-search", text="deployment rollback guide", archive_id="a2"
    )
    # vector returns p1, LIKE matches both
    env.fake.search_results = [{"id": p1.id}]
    results = await env.svc.search_archival_memories("pm-search", query="deployment")
    ids = [p.id for p in results]
    assert p1.id in ids
    assert any(c == "archival" for c, _ in env.fake.access_updates)

    # archive_id filter narrows results
    only_a2 = await env.svc.search_archival_memories(
        "pm-search", query="deployment", archive_id="a2"
    )
    assert [p.id for p in only_a2] == [p2.id]


async def test_search_archival_vector_raises(env) -> None:
    p = await env.svc.create_archival_passage(
        user_id="pm-search-err", text="x marks the spot", archive_id="a1"
    )
    env.fake.fail_search = True
    results = await env.svc.search_archival_memories("pm-search-err", query="marks")
    assert [q.id for q in results] == [p.id]


async def test_search_archival_vector_empty_uses_like(env) -> None:
    p = await env.svc.create_archival_passage(
        user_id="pm-search-empty", text="deployment runbook", archive_id="a1"
    )
    env.fake.search_results = []
    results = await env.svc.search_archival_memories("pm-search-empty", query="deployment")
    assert [q.id for q in results] == [p.id]


async def test_search_archival_no_query(env) -> None:
    p = await env.svc.create_archival_passage(
        user_id="pm-search2", text="anything at all", archive_id="a1"
    )
    results = await env.svc.search_archival_memories("pm-search2", query="")
    assert [x.id for x in results] == [p.id]


async def test_archival_by_tags(env) -> None:
    tagged = await env.svc.create_archival_passage(
        user_id="pm-tags", text="tagged", archive_id="a", tags=["alpha"]
    )
    await env.svc.create_archival_passage(
        user_id="pm-tags", text="other", archive_id="a", tags=["beta"]
    )
    results = await env.svc.get_archival_by_tags("pm-tags", ["alpha"])
    assert [p.id for p in results] == [tagged.id]


async def test_decay_recency_by_access(env) -> None:
    with_access = await env.svc.create_episodic_memory(user_id="pm-access", content="a")
    never = await env.svc.create_episodic_memory(user_id="pm-access", content="b")
    async with env.maker() as db:
        row = await db.get(EpisodicMemory, with_access.id)
        row.last_accessed_at = datetime.now(UTC) - timedelta(days=3)
        await db.commit()

    updated = await env.svc.decay_recency_by_access()
    assert updated >= 1
    reloaded = await _get_memory(env, with_access.id)
    assert reloaded.recency_score == 1.0 / 4.0
    untouched = await _get_memory(env, never.id)
    assert untouched.recency_score == 1.0


async def test_retrieve_logs_retrieval(env) -> None:
    await env.svc.create_episodic_memory(user_id="pm-logs", content="logging check content")
    await env.svc.retrieve_memories("pm-logs", query="logging", session_id="sess")
    async with env.maker() as db:
        logs = (
            (
                await db.execute(
                    select(MemoryRetrievalLog).where(MemoryRetrievalLog.user_id == "pm-logs")
                )
            )
            .scalars()
            .all()
        )
    assert logs
    assert logs[0].session_id == "sess"
