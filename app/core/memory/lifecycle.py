"""Full memory lifecycle management.

Handles the complete memory lifecycle: write -> index -> retrieve -> decay -> forget -> archive.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, and_, select
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base, async_session

logger = structlog.get_logger()


@dataclass
class MemoryWriteResult:
    """Result of a memory write operation."""

    memory_id: str
    content: str
    user_id: str
    agent_id: str
    memory_type: str
    importance: float
    created_at: str


@dataclass
class MemoryRetrieveResult:
    """Result of a memory retrieval operation."""

    memory_id: str
    content: str
    importance: float
    agent_id: str = ""
    score: float = 0.0
    memory_type: str = ""
    created_at: str = ""


@dataclass
class DecayReport:
    """Report of memory decay operation."""

    total_memories: int
    decayed_count: int
    avg_importance_before: float
    avg_importance_after: float


@dataclass
class ArchiveReport:
    """Report of archive operation."""

    archived_count: int
    remaining_count: int
    threshold_days: int


class MemoryRecord(Base):
    """SQLAlchemy model for lifecycle-managed memories."""

    __tablename__ = "lifecycle_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), default="general")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    days_since_access: Mapped[int] = mapped_column(Integer, default=0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    forgotten_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MemoryLifecycleManager:
    """Manages the full memory lifecycle.

    Implements write, index, retrieve, decay, forget, and archive
    operations with the decay formula:
        new_importance = importance * (0.95 ^ days_since_last_access)
    """

    DECAY_BASE = 0.95

    async def write_memory(
        self,
        content: str,
        user_id: str,
        agent_id: str = "",
        memory_type: str = "general",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryWriteResult:
        """Create a new memory entry."""
        memory_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        async with async_session() as db:
            record = MemoryRecord(
                id=memory_id,
                user_id=user_id,
                agent_id=agent_id or None,
                content=content[:4000],
                memory_type=memory_type,
                importance=importance,
                metadata_=metadata or {},
                created_at=now,
                updated_at=now,
            )
            db.add(record)
            await db.commit()
        logger.info("memory_written", memory_id=memory_id, user_id=user_id)
        return MemoryWriteResult(
            memory_id=memory_id,
            content=content,
            user_id=user_id,
            agent_id=agent_id,
            memory_type=memory_type,
            importance=importance,
            created_at=now.isoformat(),
        )

    async def index_memory(self, memory_id: str) -> bool:
        """Mark a memory as indexed (ready for retrieval).

        In production this would add to vector store. Here we track
        the indexing state in metadata.
        """
        async with async_session() as db:
            record = await db.get(MemoryRecord, memory_id)
            if not record:
                return False
            record.metadata_ = {
                **(record.metadata_ or {}),
                "indexed": True,
                "indexed_at": datetime.now(UTC).isoformat(),
            }
            record.updated_at = datetime.now(UTC)
            await db.commit()
        logger.info("memory_indexed", memory_id=memory_id)
        return True

    async def retrieve_memories(
        self,
        query: str,
        user_id: str,
        agent_id: str = "",
        limit: int = 10,
    ) -> list[MemoryRetrieveResult]:
        """Retrieve memories with semantic-like filtering.

        Uses keyword matching and importance scoring for ranking.
        """
        async with async_session() as db:
            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.is_archived == False,
                    MemoryRecord.is_forgotten == False,
                )
            )
            if agent_id:
                stmt = stmt.where(MemoryRecord.agent_id == agent_id)
            result = await db.execute(stmt)
            records = result.scalars().all()

            query_lower = query.lower()
            query_words = {w for w in query_lower.split() if len(w) > 2}
            scored: list[tuple[float, MemoryRecord]] = []

            for record in records:
                content_lower = record.content.lower()
                score = record.importance

                if query_words:
                    matches = sum(1 for w in query_words if w in content_lower)
                    if matches > 0:
                        score *= (1.0 + matches / len(query_words))
                    else:
                        score *= 0.1

                scored.append((score, record))

            scored.sort(key=lambda x: x[0], reverse=True)
            now = datetime.now(UTC)

            results = []
            for score, record in scored[:limit]:
                record.access_count += 1
                record.last_accessed_at = now
                record.updated_at = now
                results.append(MemoryRetrieveResult(
                    memory_id=record.id,
                    content=record.content,
                    importance=record.importance,
                    agent_id=record.agent_id or "",
                    score=score,
                    memory_type=record.memory_type,
                    created_at=record.created_at.isoformat() if record.created_at else "",
                ))

            await db.commit()
            return results

    async def decay_memories(self, user_id: str, agent_id: str = "") -> DecayReport:
        """Apply time-based decay to memory importance.

        Formula: new_importance = importance * (0.95 ^ days_since_last_access)
        """
        async with async_session() as db:
            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.is_archived == False,
                    MemoryRecord.is_forgotten == False,
                )
            )
            if agent_id:
                stmt = stmt.where(MemoryRecord.agent_id == agent_id)
            result = await db.execute(stmt)
            records = result.scalars().all()

            if not records:
                return DecayReport(
                    total_memories=0,
                    decayed_count=0,
                    avg_importance_before=0.0,
                    avg_importance_after=0.0,
                )

            now = datetime.now(UTC)
            total_before = 0.0
            total_after = 0.0
            decayed = 0

            for record in records:
                if record.last_accessed_at:
                    delta = now - record.last_accessed_at.replace(tzinfo=UTC) if record.last_accessed_at.tzinfo is None else now - record.last_accessed_at
                    days = delta.days
                else:
                    days = 0

                record.days_since_access = days
                old_importance = record.importance
                new_importance = old_importance * (self.DECAY_BASE ** days)

                if new_importance < old_importance:
                    record.importance = round(new_importance, 6)
                    decayed += 1

                total_before += old_importance
                total_after += record.importance

            await db.commit()
            count = len(records)
            return DecayReport(
                total_memories=count,
                decayed_count=decayed,
                avg_importance_before=round(total_before / count, 6) if count else 0.0,
                avg_importance_after=round(total_after / count, 6) if count else 0.0,
            )

    async def forget_memory(self, memory_id: str) -> bool:
        """Soft-delete a memory with audit trail."""
        async with async_session() as db:
            record = await db.get(MemoryRecord, memory_id)
            if not record:
                return False
            record.is_forgotten = True
            record.forgotten_at = datetime.now(UTC)
            record.metadata_ = {
                **(record.metadata_ or {}),
                "forgotten": True,
                "forgotten_at": datetime.now(UTC).isoformat(),
            }
            record.updated_at = datetime.now(UTC)
            await db.commit()
        logger.info("memory_forgotten", memory_id=memory_id)
        return True

    async def archive_old_memories(
        self,
        user_id: str,
        agent_id: str = "",
        threshold_days: int = 30,
    ) -> ArchiveReport:
        """Move old, low-importance memories to archive state."""
        async with async_session() as db:
            cutoff = datetime.now(UTC).timestamp() - (threshold_days * 86400)
            cutoff_dt = datetime.fromtimestamp(cutoff, tz=UTC)

            stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.is_archived == False,
                    MemoryRecord.is_forgotten == False,
                    MemoryRecord.created_at < cutoff_dt,
                    MemoryRecord.importance < 0.3,
                )
            )
            if agent_id:
                stmt = stmt.where(MemoryRecord.agent_id == agent_id)
            result = await db.execute(stmt)
            records = result.scalars().all()

            archived = 0
            now = datetime.now(UTC)
            for record in records:
                record.is_archived = True
                record.archived_at = now
                record.metadata_ = {
                    **(record.metadata_ or {}),
                    "archived": True,
                    "archived_at": now.isoformat(),
                    "archive_reason": f"age > {threshold_days} days, importance < 0.3",
                }
                record.updated_at = now
                archived += 1

            await db.commit()

            remaining_stmt = select(MemoryRecord).where(
                and_(
                    MemoryRecord.user_id == user_id,
                    MemoryRecord.is_archived == False,
                    MemoryRecord.is_forgotten == False,
                )
            )
            remaining_result = await db.execute(remaining_stmt)
            remaining = len(remaining_result.scalars().all())

        logger.info("memories_archived", archived=archived, user_id=user_id)
        return ArchiveReport(
            archived_count=archived,
            remaining_count=remaining,
            threshold_days=threshold_days,
        )
