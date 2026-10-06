"""Tests for structured session archiving.

Archives persist to ``session_archives`` with a one-line summary, a filtered
message list and a ``memory_diff``-style change log. The embedded extractor is
given a disabled semantic index so no vector store is touched.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.core.memory_archive.archive import SessionArchiveService
from app.core.memory_archive.index import SemanticIndex


@pytest.fixture(autouse=True)
def offline_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    class _InertVector:
        async def add(self, *_args: Any, **_kwargs: Any):
            return ""

        async def search(self, *_args: Any, **_kwargs: Any):
            return []

        async def update_access(self, *_args: Any, **_kwargs: Any):
            return None

    monkeypatch.setattr("app.core.persistent_memory.vector_memory", _InertVector())


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _archiver() -> SessionArchiveService:
    from app.core.memory_archive.extraction import MemoryExtractor

    return SessionArchiveService(extractor=MemoryExtractor(semantic=SemanticIndex(enabled=False)))


def _messages() -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "I prefer weekly release notes."},
        {"role": "assistant", "content": "The project uses FastAPI with async sessions."},
        {"role": "tool", "content": "tool result that must be filtered out."},
        {"role": "user", "content": "   "},
    ]


def test_archive_round_trip_with_summary_and_diff() -> None:
    user = "user-archive-roundtrip"
    session = "session-archive-roundtrip-0001"
    service = _archiver()

    payload = _run(
        service.archive(user, session, _messages(), title="weekly release notes")
    )
    assert payload["session_id"] == session
    assert payload["message_count"] == 3
    assert payload["one_line_summary"] == "weekly release notes"
    assert payload["archive_status"] == "completed"
    assert payload["memory_diff"]["archive_uri"] == f"sessions/{session}"
    assert payload["memory_diff"]["summary"] == {
        "user_preference": 1,
        "project_fact": 1,
        "skill_experience": 0,
    }

    fetched = _run(service.get(user, payload["id"]))
    assert fetched is not None
    assert fetched["messages"] == payload["messages"]
    assert {record["role"] for record in fetched["messages"]} == {"system", "user", "assistant"}


def test_archive_one_line_falls_back_to_first_user_message() -> None:
    user = "user-archive-fallback"
    session = "session-archive-fallback-0001"
    payload = _run(
        _archiver().archive(
            user,
            session,
            [{"role": "user", "content": "Explain the login flow in detail please."}],
        )
    )
    assert payload["one_line_summary"] == "Explain the login flow in detail please."
    assert payload["message_count"] == 1


def test_list_by_session_newest_first_and_latest() -> None:
    user = "user-archive-list"
    session = "session-archive-list-0001"
    service = _archiver()
    first = _run(service.archive(user, session, [{"role": "user", "content": "first user note"}]))
    second = _run(service.archive(user, session, [{"role": "user", "content": "second user note"}]))

    rows = _run(service.list_by_session(user, session))
    assert [row["id"] for row in rows] == [second["id"], first["id"]]
    assert "messages" not in rows[0] or rows[0]["messages"] == []

    latest = _run(service.latest(user, session))
    assert latest is not None
    assert latest["id"] == second["id"]


def test_archive_get_is_user_scoped() -> None:
    service = _archiver()
    other = _run(
        service.archive(
            "user-archive-a",
            "session-archive-a-0001",
            [{"role": "user", "content": "private user note"}],
        )
    )
    assert _run(service.get("user-archive-b", other["id"])) is None
