"""Memory reflection service — automatic memory consolidation and insight extraction.

- Letta 自动反思机制（memory consolidation）
- Hermes-Agent 记忆系统
- OpenCode 记忆管理
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vector_memory import vector_memory
from app.storage import async_session
from app.storage.models_memory import EpisodicMemory

logger = structlog.get_logger()


class MemoryReflectionService:
    """Periodically consolidate and reflect on stored memories.

    Triggers:
    - Memory count exceeds threshold
    - Time-based periodic reflection
    - After session completion
    """

    def __init__(self, reflection_interval: int = 3600, memory_threshold: int = 50, vector_memory: Any = None):
        self.reflection_interval = reflection_interval  # seconds
        self.memory_threshold = memory_threshold
        self.vector_memory = vector_memory
        self._last_reflection: float = 0.0

    async def maybe_reflect(self, user_id: str, force: bool = False) -> dict[str, Any]:
        """Run reflection if needed. Returns stats dict."""
        now = time.time()
        if not force and (now - self._last_reflection) < self.reflection_interval:
            return {"skipped": True, "reason": "interval_not_elapsed"}

        async with async_session() as db:
            count_result = await db.execute(
                select(func.count()).where(EpisodicMemory.user_id == user_id)
            )
            memory_count = count_result.scalar() or 0

            if not force and memory_count < self.memory_threshold:
                return {"skipped": True, "reason": "below_threshold", "count": memory_count}

            stats = await self._reflect(db, user_id)
            self._last_reflection = now
            return stats

    async def _reflect(self, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Consolidate memories and extract insights."""
        stats: dict[str, Any] = {"memories_processed": 0, "insights_created": 0}

        # Find low-importance memories that haven't been accessed recently
        result = await db.execute(
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == user_id,
                EpisodicMemory.importance < 0.3,
                EpisodicMemory.recency_score < 0.2,
            )
            .order_by(EpisodicMemory.last_accessed_at.asc())
            .limit(20)
        )
        stale_memories = result.scalars().all()

        # Group by memory_type and decay
        type_counts: dict[str, int] = {}
        for mem in stale_memories:
            mem.recency_score *= 0.8  # decay stale memories faster
            type_counts[mem.memory_type] = type_counts.get(mem.memory_type, 0) + 1
            stats["memories_processed"] += 1

        # Create insight if we found patterns
        if type_counts:
            dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
            summary = f"Reflection: {stats['memories_processed']} stale memories processed. Dominant type: {dominant_type}."
            await self._add_reflection_memory(db, user_id, summary)
            stats["insights_created"] = 1

        await db.commit()
        logger.info("Memory reflection complete", **stats)
        return stats

    async def _add_reflection_memory(self, db: AsyncSession, user_id: str, content: str) -> EpisodicMemory:
        """Add a system-generated reflection memory."""
        memory = EpisodicMemory(
            user_id=user_id,
            content=content,
            summary=content[:200],
            memory_type="reflection",
            importance=0.6,
        )
        db.add(memory)
        return memory

    async def reflect_on_task(
        self,
        user_id: str,
        task_description: str,
        outcome: str,
        success: bool = True,
        blockers: list[str] | None = None,
        improvements: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate structured reflection after task completion.

        """
        blockers = blockers or []
        improvements = improvements or []

        success_strategies = []
        if success:
            success_strategies.append(f"Completed task: {task_description}")

        reflection_text = (
            f"Task: {task_description}\n"
            f"Outcome: {outcome}\n"
            f"Success: {success}\n"
            f"Strategies: {', '.join(success_strategies)}\n"
            f"Blockers: {', '.join(blockers)}\n"
            f"Improvements: {', '.join(improvements)}"
        )

        async with async_session() as db:
            memory = EpisodicMemory(
                user_id=user_id,
                content=reflection_text,
                summary=reflection_text[:200],
                memory_type="task_reflection",
                importance=0.8 if success else 0.5,
            )
            db.add(memory)
            await db.commit()
            await db.refresh(memory)

            await vector_memory.add(
                collection="reflection",
                doc_id=memory.id,
                text=reflection_text,
                metadata={
                    "user_id": user_id,
                    "memory_id": memory.id,
                    "success": success,
                    "blockers": blockers,
                    "improvements": improvements,
                    "task_description": task_description,
                },
            )

        logger.info(
            "task_reflection_recorded",
            user_id=user_id,
            task=task_description,
            success=success,
        )
        return {
            "memory_id": memory.id,
            "success": success,
            "blockers": blockers,
            "improvements": improvements,
        }

    async def get_similar_reflections(
        self,
        user_id: str,
        task_description: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve similar past reflections for a new task."""
        return await vector_memory.search(
            collection="reflection",
            query=task_description,
            top_k=limit,
            where={"user_id": user_id},
        )


# Global singleton
memory_reflection = MemoryReflectionService()
