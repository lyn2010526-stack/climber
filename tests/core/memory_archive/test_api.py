"""HTTP-level tests for the memory-archive endpoints.

The API singletons are pointed at inert semantic indexes so the whole flow
runs credential- and vector-free; keyword fallback provides the search hits.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.memory_archive.index import SemanticIndex


@pytest.fixture(autouse=True)
def offline_semantic(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1 import memory_archive as module

    class _InertVector:
        async def add(self, *_args: Any, **_kwargs: Any):
            return ""

        async def search(self, *_args: Any, **_kwargs: Any):
            return []

        async def update_access(self, *_args: Any, **_kwargs: Any):
            return None

    disabled = SemanticIndex(enabled=False)
    monkeypatch.setattr(module._sidecars, "_semantic", disabled)
    monkeypatch.setattr(module._retriever, "_semantic", disabled)
    monkeypatch.setattr(module._archiver._extractor, "_semantic", disabled)
    monkeypatch.setattr(module._bypass._retriever, "_semantic", disabled)
    monkeypatch.setattr("app.core.persistent_memory.vector_memory", _InertVector())



async def test_refresh_and_read_sidecars(client) -> None:
    payload = {
        "entries": [
            {"path": "auth.md", "content": "OAuth 2.0 flows protect the API surface."},
            {"path": "login.md", "content": "The login endpoint requires a token."},
        ]
    }
    response = await client.post("/api/v1/memory/sidecars/reference", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["abstract_level"] == 0
    assert data["overview_level"] == 1
    assert data["entry_count"] == 2

    read = await client.get("/api/v1/memory/sidecars/reference")
    assert read.status_code == 200
    records = read.json()["records"]
    assert len(records) == 2
    assert {record["level"] for record in records} == {0, 1}



async def test_search_falls_back_to_sidecar_keywords(client) -> None:
    await client.post(
        "/api/v1/memory/sidecars/auth",
        json={
            "entries": [
                {"path": "tokens.md", "content": "Refresh tokens are rotated on every use."},
            ]
        },
    )
    result = await client.get(
        "/api/v1/memory/search",
        params={"scope": "auth", "query": "rotated"},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["scope"] == "auth"
    assert body["total"] >= 1
    assert "rotated" in body["hits"][0]["text"].lower()



async def test_create_and_fetch_archive(client) -> None:
    payload = {
        "session_id": "session-api-0001",
        "title": "api session",
        "messages": [
            {"role": "user", "content": "I prefer concise API commit messages."},
            {"role": "assistant", "content": "The project uses FastAPI with async sessions."},
        ],
    }
    created = await client.post("/api/v1/memory/archives", json=payload)
    assert created.status_code == 200
    archive = created.json()
    assert archive["session_id"] == "session-api-0001"
    assert archive["one_line_summary"] == "api session"
    assert archive["memory_diff"]["summary"]["user_preference"] == 1

    fetched = await client.get(f"/api/v1/memory/archives/{archive['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == archive["id"]

    listed = await client.get(
        "/api/v1/memory/archives", params={"session_id": "session-api-0001"}
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1



async def test_context_bundle_endpoint(client) -> None:
    await client.post(
        "/api/v1/memory/sidecars/reference",
        json={
            "entries": [
                {"path": "auth.md", "content": "OAuth 2.0 flows protect the API surface."},
            ]
        },
    )
    bundle = await client.get("/api/v1/memory/context-bundle")
    assert bundle.status_code == 200
    body = bundle.json()
    assert body["injected_summaries"] == 1
    assert "## Archived Memory Context" in body["content"]
    assert "OAuth 2.0 flows protect" in body["content"]



async def test_unknown_archive_is_404(client) -> None:
    response = await client.get("/api/v1/memory/archives/does-not-exist")
    assert response.status_code == 404
