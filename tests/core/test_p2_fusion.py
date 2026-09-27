"""P2 fusion tests: memory agent-scope isolation and main-content extraction.

Memory scope: retrieve_memories(agent_id=...) must isolate by agent, and
omitting agent_id must preserve the historical single-pool behavior.
Extraction: clean_web_content/extract_main_content must select article bodies
from real HTML while keeping the legacy line-filter output byte-identical.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.persistent_memory import persistent_memory
from app.core.web_content_cleaner import clean_web_content, extract_main_content


class FakeVector:
    """Vector store stub that honors user_id + agent_id metadata filters."""

    def __init__(self) -> None:
        self.added: list[tuple[str, str, str, dict[str, Any]]] = []
        self.search_calls: list[dict[str, Any]] = []
        self.records: dict[str, dict[str, dict[str, Any]]] = {}

    async def add(self, collection: str, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> str:
        self.added.append((collection, str(doc_id), text, metadata or {}))
        self.records.setdefault(collection, {})[str(doc_id)] = {"text": text, "metadata": metadata or {}}
        return str(doc_id)

    async def search(self, collection: str, query: str, top_k: int = 5, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        self.search_calls.append({"collection": collection, "query": query, "where": where})
        results = []
        for doc_id, rec in self.records.get(collection, {}).items():
            if where:
                if rec["metadata"].get("user_id") != where.get("user_id"):
                    continue
                if "agent_id" in where and rec["metadata"].get("agent_id") != where["agent_id"]:
                    continue
            results.append({"id": doc_id, "text": rec["text"], "metadata": rec["metadata"], "score": 0.9})
        return results[:top_k]


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _ensure_agents(*agent_ids: str, user_id: str) -> None:
    """Insert real agents rows so EpisodicMemory.agent_id FK holds (SQLite FK on)."""
    from app.storage import async_session
    from app.storage.database import Agent

    async def _inner() -> None:
        async with async_session() as db:
            for agent_id in agent_ids:
                db.add(Agent(id=agent_id, user_id=user_id, name=agent_id, provider="openai", model_id="gpt-4o"))
            await db.commit()

    _run(_inner())


# ─── Memory scope isolation ────────────────────────────────────────────────


def test_agent_scope_isolates_retrieval(monkeypatch: Any) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-scope"
    _ensure_agents("agent-1", "agent-2", user_id=user)

    a1 = _run(persistent_memory.create_episodic_memory(
        user_id=user, content="alpha agent note about widgets", agent_id="agent-1", importance=0.8,
    ))
    a2 = _run(persistent_memory.create_episodic_memory(
        user_id=user, content="alpha agent note from another agent", agent_id="agent-2", importance=0.8,
    ))

    scoped_1 = _run(persistent_memory.retrieve_memories(user, query="widgets", agent_id="agent-1"))
    scoped_2 = _run(persistent_memory.retrieve_memories(user, query="widgets", agent_id="agent-2"))

    assert [m.id for m in scoped_1] == [a1.id]
    assert [m.id for m in scoped_2] == [a2.id]


def test_scope_filter_wired_into_vector_and_db(monkeypatch: Any) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    _ensure_agents("agent-9", user_id="u")
    _run(persistent_memory.create_episodic_memory(
        user_id="u", content="scoped widget note", agent_id="agent-9", importance=0.7,
    ))
    _run(persistent_memory.retrieve_memories("u", query="widget", agent_id="agent-9"))
    scoped_where = [c["where"] for c in fake.search_calls if c["where"] and "agent_id" in c["where"]]
    assert scoped_where and scoped_where[-1]["agent_id"] == "agent-9"
    # agent_id recorded in vector metadata at write time.
    assert any(meta.get("agent_id") == "agent-9" for _, _, _, meta in fake.added)


def test_omitting_agent_scope_preserves_shared_pool(monkeypatch: Any) -> None:
    """Backward compatibility: without agent_id, all agents share one pool."""
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    user = "user-shared"
    _ensure_agents("agent-1", "agent-2", user_id=user)

    a1 = _run(persistent_memory.create_episodic_memory(
        user_id=user, content="shared pool widget note one", agent_id="agent-1", importance=0.5,
    ))
    a2 = _run(persistent_memory.create_episodic_memory(
        user_id=user, content="shared pool widget note two", agent_id="agent-2", importance=0.5,
    ))

    returned = _run(persistent_memory.retrieve_memories(user, query="widget"))
    ids = {m.id for m in returned}
    assert {a1.id, a2.id} <= ids
    # No agent filter was applied.
    assert all("agent_id" not in (c["where"] or {}) for c in fake.search_calls)


def test_other_user_never_sees_scoped_memory(monkeypatch: Any) -> None:
    fake = FakeVector()
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", fake)
    _ensure_agents("agent-1", user_id="owner")
    _run(persistent_memory.create_episodic_memory(
        user_id="owner", content="private widget note", agent_id="agent-1", importance=0.9,
    ))
    assert _run(persistent_memory.retrieve_memories("intruder", query="widget", agent_id="agent-1")) == []


# ─── Main-content extraction ───────────────────────────────────────────────


ARTICLE_HTML = """
<html><head><title>Widget Guide</title></head>
<body>
<nav>Home | Products | About</nav>
<article>
<h1>Understanding Widgets</h1>
<p>Widgets are small components. They can be composed into larger systems.</p>
<p>This paragraph explains the second important detail about widgets in depth.</p>
</article>
<footer>Copyright 2026 Example Inc.</footer>
</body></html>
"""


def test_extract_main_content_selects_article_body() -> None:
    text = extract_main_content(ARTICLE_HTML)
    assert "Widgets are small components" in text
    assert "second important detail" in text
    assert "Home | Products" not in text
    assert "Copyright 2026" not in text


def test_extract_main_content_plain_text_is_legacy() -> None:
    plain = "Line one.\nLine two."
    assert extract_main_content(plain) == clean_web_content("", plain)


def test_clean_web_content_legacy_path_unchanged() -> None:
    text = "subscribe to our newsletter\nReal content line here.\nmenu"
    assert clean_web_content("", text) == "Real content line here."


def test_clean_web_content_uses_html_when_provided() -> None:
    cleaned = clean_web_content(ARTICLE_HTML, "")
    assert "Widgets are small components" in cleaned
    assert "Home | Products" not in cleaned


def test_malformed_html_falls_back_without_raising() -> None:
    broken = "<article><p>unclosed paragraph about widgets and systems"
    out = extract_main_content(broken, fallback_text="fallback line")
    assert isinstance(out, str)


def test_script_only_html_returns_empty() -> None:
    assert extract_main_content("<script>var x = 1;</script>") == ""


def test_multi_language_nav_boilerplate_removed() -> None:
    html = (
        "<div><nav>Menú principal · Inicio · Productos</nav>"
        "<article><p>Este artículo describe los widgets y su composición en sistemas mayores.</p></article>"
        "<footer>Aviso legal</footer></div>"
    )
    text = extract_main_content(html)
    assert "describe los widgets" in text
    assert "Menú principal" not in text
