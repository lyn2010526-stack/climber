"""Session archiving with memory extraction on commit.

Mirrors the OpenViking session lifecycle: a committed conversation is archived
as one structured record carrying a one-line summary and a ``memory_diff``-style
change log, then extractable memories land in ``episodic_memories`` and the
directory semantic index so later sessions can retrieve them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.core.memory_archive.extraction import MemoryExtractor
from app.storage import async_session
from app.storage.models_memory_archive import SessionArchive

logger = structlog.get_logger()

SUMMARY_MAX_CHARS = 160


class SessionArchiveService:
    """Archive sessions and extract long-term memories from them."""

    def __init__(self, extractor: MemoryExtractor | None = None) -> None:
        self._extractor = extractor or MemoryExtractor()

    async def archive(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
        *,
        title: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist one structured session archive with its memory diff."""
        records = [
            self._to_record(message) for message in (messages or []) if self._is_archivable(message)
        ]
        one_line = self._one_line_summary(records, title)
        stats = await self._extractor.extract(user_id, session_id, records, agent_id=agent_id)
        memory_diff = {
            "archive_uri": f"sessions/{session_id}",
            "extracted_at": datetime.now(UTC).isoformat(),
            "operations": {"adds": [], "updates": [], "deletes": []},
            "summary": stats,
        }
        async with async_session() as db:
            row = SessionArchive(
                user_id=user_id,
                session_id=session_id,
                title=title,
                one_line_summary=one_line,
                message_count=len(records),
                messages=records,
                memory_diff=memory_diff,
                archive_status="completed",
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
        logger.info(
            "session_archived", user_id=user_id, session_id=session_id, messages=len(records)
        )
        return self._payload(row)

    async def get(self, user_id: str, archive_id: str) -> dict[str, Any] | None:
        async with async_session() as db:
            row = (
                await db.execute(
                    select(SessionArchive).where(
                        SessionArchive.user_id == user_id,
                        SessionArchive.id == archive_id,
                    )
                )
            ).scalar_one_or_none()
        return self._payload(row) if row else None

    async def list_by_session(
        self,
        user_id: str,
        session_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        async with async_session() as db:
            rows = list(
                (
                    await db.execute(
                        select(SessionArchive)
                        .where(
                            SessionArchive.user_id == user_id,
                            SessionArchive.session_id == session_id,
                        )
                        .order_by(SessionArchive.created_at.desc(), SessionArchive.id.desc())
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        return [self._payload(row, include_messages=False) for row in rows]

    async def latest(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        rows = await self.list_by_session(user_id, session_id, limit=1)
        return rows[0] if rows else None

    @staticmethod
    def _to_record(message: dict[str, Any]) -> dict[str, Any]:
        return {
            "role": message.get("role", "user"),
            "content": (message.get("content") or ""),
        }

    @staticmethod
    def _is_archivable(message: dict[str, Any]) -> bool:
        role = message.get("role")
        content = (message.get("content") or "").strip()
        return role in ("user", "assistant", "system") and bool(content)

    @staticmethod
    def _one_line_summary(records: list[dict[str, Any]], title: str | None) -> str:
        if title and title.strip():
            return " ".join(title.split())[:SUMMARY_MAX_CHARS]
        for record in records:
            if record.get("role") == "user":
                text = " ".join(record["content"].split())
                if text:
                    return text[:SUMMARY_MAX_CHARS]
        return "Completed agent session."

    @staticmethod
    def _payload(row: SessionArchive, *, include_messages: bool = True) -> dict[str, Any]:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "session_id": row.session_id,
            "title": row.title,
            "one_line_summary": row.one_line_summary,
            "message_count": row.message_count,
            "messages": row.messages if include_messages else [],
            "memory_diff": row.memory_diff,
            "archive_status": row.archive_status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


# Global singleton
session_archive = SessionArchiveService()
