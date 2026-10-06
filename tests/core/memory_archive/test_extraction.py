"""Tests for session memory extraction.

Classification is pure; persistence is verified against the real
``episodic_memories`` table with the semantic index disabled so the tests
stay offline.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sqlalchemy import select

from app.core.memory_archive.extraction import (
    MEMORY_SCOPE,
    MemoryExtractor,
)
from app.core.memory_archive.index import SemanticIndex
from app.storage import async_session
from app.storage.models_memory import EpisodicMemory


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


def _extractor() -> MemoryExtractor:
    return MemoryExtractor(semantic=SemanticIndex(enabled=False))


def _message(role: str, content: str) -> dict[str, Any]:
    return {"role": role, "content": content}


def test_classify_user_preference_signal() -> None:
    messages = [_message("user", "I prefer dark mode in dashboards at night.")]
    extracted = _extractor().classify(messages)
    assert len(extracted) == 1
    assert extracted[0].memory_type == "user_preference"


def test_classify_project_fact_signal() -> None:
    messages = [_message("assistant", "The project uses FastAPI with async sessions.")]
    extracted = _extractor().classify(messages)
    assert extracted[0].memory_type == "project_fact"


def test_classify_skill_experience_signal() -> None:
    messages = [_message("user", "I learned that retries work best with backoff.")]
    extracted = _extractor().classify(messages)
    assert extracted[0].memory_type == "skill_experience"


def test_classify_ignores_short_blips() -> None:
    assert _extractor().classify([_message("user", "I like tea")]) == []


def test_classify_takes_first_matching_category_only() -> None:
    messages = [{"role": "user", "content": "I prefer FastAPI and the project uses Postgres."}]
    extracted = _extractor().classify(messages)
    assert len(extracted) == 1
    assert extracted[0].memory_type == "user_preference"


def test_extract_persists_episodic_memories() -> None:
    user = "user-extract-persist"
    session = "session-extract-0001"
    messages = [
        _message("user", "I prefer concise commit messages for the release notes."),
        _message("assistant", "The codebase uses ruff with a line length of 100."),
        _message("user", "I learned that baseline tests must stay above 1100."),
        _message("user", "please remember this deployment detail for later usage."),
    ]
    stats = _run(_extractor().extract(user, session, messages))

    assert stats == {"user_preference": 2, "project_fact": 1, "skill_experience": 1}

    async def _load() -> list[EpisodicMemory]:
        async with async_session() as db:
            return list((await db.execute(
                select(EpisodicMemory).where(EpisodicMemory.source_session_id == session)
            )).scalars().all())

    rows = _run(_load())
    assert len(rows) == 4
    assert {row.memory_type for row in rows} == {
        "user_preference",
        "project_fact",
        "skill_experience",
    }
    assert all("extracted" in (row.tags or []) for row in rows)
    assert any(row.memory_type == "user_preference" for row in rows)


def test_extract_with_no_signals_is_empty() -> None:
    user = "user-extract-empty"
    session = "session-extract-empty-0001"
    messages = [
        _message("user", "Could you double check the timeout value in the config file?"),
    ]
    stats = _run(_extractor().extract(user, session, messages))
    assert stats["user_preference"] == 0
    assert stats["project_fact"] == 0
    assert stats["skill_experience"] == 0


def test_extracted_scope_metadata_is_memory() -> None:
    from app.storage.models_memory import EpisodicMemory as E

    user = "user-extract-meta"
    session = "session-extract-meta-0001"
    _run(
        _extractor().extract(
            user, session, [_message("user", "I work on the search ranking team.")]
        )
    )

    async def _load() -> EpisodicMemory:
        async with async_session() as db:
            return (await db.execute(
                select(E).where(E.source_session_id == session)
            )).scalars().one()

    row = _run(_load())
    assert row.memory_type == "project_fact"
    assert (row.metadata_ or {}).get("scope") == MEMORY_SCOPE
