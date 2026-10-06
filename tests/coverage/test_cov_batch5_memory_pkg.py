"""Coverage tests for app/memory/__init__.py (SessionMemory/LongTermMemory/VectorMemory)."""

from __future__ import annotations

from typing import Any

from app.memory import LongTermMemory, SessionMemory, VectorMemory

# ── SessionMemory ─────────────────────────────────────────────────────────


def test_session_memory_add_and_context() -> None:
    mem = SessionMemory(max_messages=4)
    mem.add("user", "hello", extra="meta")
    mem.add("assistant", "hi")
    ctx = mem.get_context()
    assert ctx[0] == {"role": "user", "content": "hello", "extra": "meta"}
    assert ctx[1]["content"] == "hi"


def test_session_memory_get_context_last_n() -> None:
    mem = SessionMemory(max_messages=10)
    for i in range(5):
        mem.add("user", f"m{i}")
    assert [m["content"] for m in mem.get_context(last_n=2)] == ["m3", "m4"]
    # last_n falsy -> returns all
    assert len(mem.get_context(last_n=0)) == 5


def test_session_memory_clear_and_truncate() -> None:
    mem = SessionMemory(max_messages=10)
    for i in range(5):
        mem.add("user", f"m{i}")
    mem.truncate(keep_n=2)
    assert [m["content"] for m in mem.get_context()] == ["m3", "m4"]
    mem.clear()
    assert mem.get_context() == []


def test_session_memory_persist_callback_success_and_failure() -> None:
    seen: list[dict[str, Any]] = []

    def callback(message: dict[str, Any]) -> None:
        seen.append(message)

    mem = SessionMemory(persist_callback=callback)
    mem.add("user", "persisted")
    assert seen and seen[0]["content"] == "persisted"

    def boom(message: dict[str, Any]) -> None:
        raise RuntimeError("persist failed")

    mem2 = SessionMemory(persist_callback=boom)
    # Exception is suppressed, message still stored
    mem2.add("user", "kept")
    assert mem2.get_context()[0]["content"] == "kept"


def test_session_memory_maxlen_drops_old() -> None:
    mem = SessionMemory(max_messages=2)
    mem.add("user", "a")
    mem.add("user", "b")
    mem.add("user", "c")
    assert [m["content"] for m in mem.get_context()] == ["b", "c"]


# ── LongTermMemory ────────────────────────────────────────────────────────


def test_long_term_memory_facts() -> None:
    mem = LongTermMemory()
    assert mem.get_facts("u1") == []
    assert mem.format_for_prompt("u1") == ""

    mem.add_fact("u1", "likes tea", category="food")
    mem.add_fact("u1", "works remotely")
    facts = mem.get_facts("u1")
    assert facts[0] == {"fact": "likes tea", "category": "food"}
    assert facts[1]["category"] == "general"

    formatted = mem.format_for_prompt("u1")
    assert formatted.startswith("## Known Facts:")
    assert "[food] likes tea" in formatted


def test_long_term_memory_limit() -> None:
    mem = LongTermMemory()
    for i in range(25):
        mem.add_fact("u", f"fact-{i}")
    assert len(mem.get_facts("u", limit=5)) == 5
    assert mem.get_facts("u", limit=5)[-1]["fact"] == "fact-24"


# ── VectorMemory ──────────────────────────────────────────────────────────


class _FakeCollection:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []
        self.query_error: Exception | None = None
        self.query_result: dict[str, Any] = {"documents": [["doc-a", "doc-b"]]}

    def add(self, documents: list[str], ids: list[str], metadatas: Any) -> None:
        self.added.append({"documents": documents, "ids": ids, "metadatas": metadatas})

    def query(self, query_texts: list[str], n_results: int) -> dict[str, Any]:
        if self.query_error is not None:
            raise self.query_error
        return self.query_result


class _FakeClient:
    def __init__(self) -> None:
        self.created: list[str] = []

    def get_or_create_collection(self, name: str) -> _FakeCollection:
        self.created.append(name)
        return _FakeCollection()


async def test_vector_memory_add_documents_generates_ids() -> None:
    vm = VectorMemory(persist_path="/tmp/unused-chroma")
    coll = _FakeCollection()
    vm._collections["c1"] = coll
    await vm.add_documents("c1", ["hello"], metadatas=[{"a": 1}])
    assert coll.added[0]["documents"] == ["hello"]
    assert len(coll.added[0]["ids"]) == 1


async def test_vector_memory_add_documents_explicit_ids() -> None:
    vm = VectorMemory()
    coll = _FakeCollection()
    vm._collections["c2"] = coll
    await vm.add_documents("c2", ["x", "y"], ids=["i1", "i2"])
    assert coll.added[0]["ids"] == ["i1", "i2"]


async def test_vector_memory_query_success() -> None:
    vm = VectorMemory()
    vm._collections["c3"] = _FakeCollection()
    out = await vm.query("c3", "text", n_results=2)
    assert out == ["doc-a", "doc-b"]


async def test_vector_memory_query_exception_returns_empty() -> None:
    vm = VectorMemory()
    coll = _FakeCollection()
    coll.query_error = RuntimeError("boom")
    vm._collections["c4"] = coll
    assert await vm.query("c4", "text") == []


async def test_vector_memory_get_client_imports_chromadb(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    created: list[str] = []

    class _PersistentClient:
        def __init__(self, path: str) -> None:
            created.append(path)

    fake_chromadb = SimpleNamespace(PersistentClient=_PersistentClient)
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)

    vm = VectorMemory(persist_path="/tmp/fake-chroma")
    client = await vm._get_client()
    assert isinstance(client, _PersistentClient)
    assert created == ["/tmp/fake-chroma"]
    # second call returns the cached client
    assert await vm._get_client() is client


async def test_vector_memory_get_collection_uses_client() -> None:
    vm = VectorMemory()
    client = _FakeClient()
    vm._client = client
    coll_first = await vm._get_collection("fresh")
    coll_second = await vm._get_collection("fresh")
    assert coll_first is coll_second
    assert client.created == ["fresh"]
    # _get_client returns the injected client unchanged
    assert await vm._get_client() is client
