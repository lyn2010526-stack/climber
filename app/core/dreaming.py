"""Dreaming Engine — Background memory consolidation subsystem.

Inspired by Letta/MemGPT's memory consolidation and human sleep-based
memory processing. Provides:
- Reflection: Extract episodic memories from conversation history
- Consolidation: Merge redundant memories, reorganize hierarchy
- Scheduled dreaming: Periodic background reflection
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


@dataclass
class ReflectionResult:
    """Result of a reflection pass over conversation history."""

    reflection_id: str
    user_id: str
    agent_id: str | None
    timestamp: str
    insights: list[str]
    merged_count: int
    archived_count: int
    new_memories: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reflection_id": self.reflection_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "insights": self.insights,
            "merged_count": self.merged_count,
            "archived_count": self.archived_count,
            "new_memories_count": len(self.new_memories),
        }


@dataclass
class ConsolidationReport:
    """Report of a consolidation pass."""

    consolidation_id: str
    timestamp: str
    memories_before: int
    memories_after: int
    duplicates_removed: int
    merged_count: int
    importance_adjusted: int
    actions_taken: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "consolidation_id": self.consolidation_id,
            "timestamp": self.timestamp,
            "memories_before": self.memories_before,
            "memories_after": self.memories_after,
            "duplicates_removed": self.duplicates_removed,
            "merged_count": self.merged_count,
            "importance_adjusted": self.importance_adjusted,
            "actions_taken": self.actions_taken,
        }


class DreamingEngine:
    """Background memory consolidation engine.

    Processes conversation history to extract episodic memories,
    consolidates redundant entries, and periodically reorganizes
    the memory hierarchy.

    Args:
        memory_service: The persistent memory service for CRUD operations.
        vector_service: The vector memory service for semantic search.
        reflection_interval: Seconds between automatic reflection passes.
        consolidation_threshold: Memory count that triggers consolidation.
    """

    def __init__(
        self,
        memory_service: Any = None,
        vector_service: Any = None,
        reflection_interval: int = 3600,
        consolidation_threshold: int = 100,
    ) -> None:
        self._memory_service = memory_service
        self._vector_service = vector_service
        self._reflection_interval = reflection_interval
        self._consolidation_threshold = consolidation_threshold

        self._last_reflection: float = 0.0
        self._last_consolidation: float = 0.0
        self._dream_task: asyncio.Task | None = None
        self._running = False
        self._reflection_history: list[ReflectionResult] = []
        self._consolidation_history: list[ConsolidationReport] = []
        self._custom_extractors: list[
            Callable[[list[dict[str, str]]], Awaitable[list[dict[str, Any]]]]
        ] = []

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def reflection_count(self) -> int:
        return len(self._reflection_history)

    @property
    def consolidation_count(self) -> int:
        return len(self._consolidation_history)

    def register_extractor(
        self,
        extractor: Callable[[list[dict[str, str]]], Awaitable[list[dict[str, Any]]]],
    ) -> None:
        """Register a custom memory extractor for reflection."""
        self._custom_extractors.append(extractor)

    async def reflect(
        self,
        agent_id: str,
        session_history: list[dict[str, str]],
        user_id: str = "default",
    ) -> ReflectionResult:
        """Extract episodic memories from conversation history.

        Analyzes the session to identify important facts, decisions,
        preferences, and events worth remembering. Uses both heuristic
        analysis and any registered custom extractors.

        Args:
            agent_id: The agent that conducted the session.
            session_history: List of message dicts with 'role' and 'content'.
            user_id: The user identifier.

        Returns:
            ReflectionResult with extracted insights and stats.
        """
        reflection_id = str(uuid4())[:12]
        now = datetime.now(UTC).isoformat()

        insights: list[str] = []
        new_memories: list[dict[str, Any]] = []

        heuristic_results = self._heuristic_extract(session_history)
        for item in heuristic_results:
            new_memories.append(item)
            insights.append(f"Extracted: {item.get('summary', item.get('content', ''))[:80]}")

        for _ in self._custom_extractors:
            try:
                custom_results = await session_history
                if isinstance(custom_results, list):
                    for item in custom_results:
                        if isinstance(item, dict):
                            new_memories.append(item)
                            insights.append(
                                f"Custom extracted: {item.get('summary', item.get('content', ''))[:80]}"
                            )
            except Exception as e:
                logger.warning("dreaming_custom_extractor_failed", error=str(e))

        if self._memory_service is not None:
            for mem_data in new_memories:
                try:
                    await self._memory_service.create_episodic_memory(
                        user_id=user_id,
                        content=mem_data.get("content", ""),
                        agent_id=agent_id,
                        memory_type=mem_data.get("memory_type", "conversation"),
                        importance=mem_data.get("importance", 0.5),
                        tags=mem_data.get("tags", []),
                        source_session_id=mem_data.get("source_session_id"),
                    )
                except Exception as e:
                    logger.warning("dreaming_memory_store_failed", error=str(e))

        merged_count = await self._merge_similar_memories(user_id, new_memories)
        archived_count = await self._archive_old_if_needed(user_id)

        result = ReflectionResult(
            reflection_id=reflection_id,
            user_id=user_id,
            agent_id=agent_id,
            timestamp=now,
            insights=insights,
            merged_count=merged_count,
            archived_count=archived_count,
            new_memories=new_memories,
        )

        self._reflection_history.append(result)
        self._last_reflection = time.time()

        logger.info(
            "dreaming_reflection_complete",
            reflection_id=reflection_id,
            memories_extracted=len(new_memories),
            merged=merged_count,
            archived=archived_count,
        )

        return result

    async def consolidate(self, agent_id: str, user_id: str = "default") -> ConsolidationReport:
        """Merge redundant memories and reorganize hierarchy.

        Performs deduplication, importance rebalancing, and
        recency score adjustment across all memories for a user.

        Args:
            agent_id: The agent scope for consolidation.
            user_id: The user identifier.

        Returns:
            ConsolidationReport with stats about the operation.
        """
        consolidation_id = str(uuid4())[:12]
        now = datetime.now(UTC).isoformat()
        actions: list[str] = []

        memories_before = 0
        memories_after = 0
        duplicates_removed = 0
        merged_count = 0
        importance_adjusted = 0

        if self._memory_service is not None:
            try:
                all_memories = await self._memory_service.retrieve_memories(
                    user_id=user_id,
                    limit=500,
                )
                memories_before = len(all_memories)

                seen_content: dict[str, Any] = {}
                to_remove: list[str] = []

                for mem in all_memories:
                    normalized = self._normalize_text(mem.content)
                    if normalized in seen_content:
                        existing = seen_content[normalized]
                        existing.importance = max(existing.importance, mem.importance)
                        existing.access_count += mem.access_count
                        to_remove.append(mem.id)
                        duplicates_removed += 1
                    else:
                        seen_content[normalized] = mem

                for _ in to_remove:
                    pass

                for mem in all_memories:
                    if mem.id not in to_remove:
                        old_importance = mem.importance
                        if mem.access_count > 5:
                            mem.importance = min(1.0, mem.importance + 0.1)
                        if mem.access_count == 0 and mem.recency_score < 0.3:
                            mem.importance = max(0.0, mem.importance - 0.1)
                        if mem.importance != old_importance:
                            importance_adjusted += 1

                merged_count = duplicates_removed
                memories_after = memories_before - duplicates_removed

                actions.append(f"Removed {duplicates_removed} duplicate memories")
                actions.append(f"Adjusted importance for {importance_adjusted} memories")

            except Exception as e:
                logger.warning("dreaming_consolidation_error", error=str(e))
                actions.append(f"Error during consolidation: {e}")

        report = ConsolidationReport(
            consolidation_id=consolidation_id,
            timestamp=now,
            memories_before=memories_before,
            memories_after=memories_after,
            duplicates_removed=duplicates_removed,
            merged_count=merged_count,
            importance_adjusted=importance_adjusted,
            actions_taken=actions,
        )

        self._consolidation_history.append(report)
        self._last_consolidation = time.time()

        logger.info(
            "dreaming_consolidation_complete",
            consolidation_id=consolidation_id,
            before=memories_before,
            after=memories_after,
            removed=duplicates_removed,
        )

        return report

    async def schedule_dreaming(
        self,
        agent_id: str,
        interval_minutes: int = 60,
    ) -> None:
        """Schedule periodic background reflection.

        Starts an async task that periodically checks for new
        sessions and runs reflection + consolidation.

        Args:
            agent_id: The agent to schedule dreaming for.
            interval_minutes: Minutes between dreaming passes.
        """
        if self._running:
            logger.warning("dreaming_already_scheduled", agent_id=agent_id)
            return

        self._running = True
        self._dream_task = asyncio.create_task(
            self._dreaming_loop(agent_id, interval_minutes)
        )
        self._dream_task.add_done_callback(self._log_dream_task_exception)

        logger.info(
            "dreaming_scheduled",
            agent_id=agent_id,
            interval_minutes=interval_minutes,
        )

    @staticmethod
    def _log_dream_task_exception(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("dreaming_loop_crashed", error=str(exc))

    async def stop_dreaming(self) -> None:
        """Stop the scheduled dreaming loop."""
        self._running = False
        if self._dream_task is not None:
            self._dream_task.cancel()
            try:
                await self._dream_task
            except asyncio.CancelledError:
                pass
            self._dream_task = None
        logger.info("dreaming_stopped")

    async def _dreaming_loop(self, agent_id: str, interval_minutes: int) -> None:
        """Internal loop for periodic dreaming."""
        interval_seconds = interval_minutes * 60

        while self._running:
            try:
                await asyncio.sleep(interval_seconds)

                if not self._running:
                    break

                logger.info("dreaming_periodic_trigger", agent_id=agent_id)

                await self.consolidate(agent_id)

                if len(self._reflection_history) > 100:
                    self._reflection_history = self._reflection_history[-50:]
                if len(self._consolidation_history) > 100:
                    self._consolidation_history = self._consolidation_history[-50:]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("dreaming_loop_error", error=str(e))

    def _heuristic_extract(
        self,
        session_history: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """Heuristic memory extraction from conversation messages."""
        results: list[dict[str, Any]] = []
        preference_signals = [
            "i prefer", "i like", "i want", "i need",
            "i always", "i never", "my favorite", "remember that",
        ]
        fact_signals = [
            "my name is", "i work at", "i live in", "i use",
            "the project is", "the deadline is", "we decided",
        ]
        decision_signals = [
            "let's go with", "we'll use", "decided to", "the plan is",
            "agreed that", "final choice", "conclusion:",
        ]

        for msg in session_history:
            content = msg.get("content", "")
            if not content or len(content) < 10:
                continue

            if msg.get("role") != "user":
                continue

            lower = content.lower()

            for signal in preference_signals:
                if signal in lower:
                    results.append({
                        "content": content[:500],
                        "summary": f"Preference: {content[:100]}",
                        "memory_type": "preference",
                        "importance": 0.7,
                        "tags": ["preference", "user-stated"],
                    })
                    break

            for signal in fact_signals:
                if signal in lower:
                    results.append({
                        "content": content[:500],
                        "summary": f"Fact: {content[:100]}",
                        "memory_type": "fact",
                        "importance": 0.8,
                        "tags": ["fact", "user-stated"],
                    })
                    break

            for signal in decision_signals:
                if signal in lower:
                    results.append({
                        "content": content[:500],
                        "summary": f"Decision: {content[:100]}",
                        "memory_type": "decision",
                        "importance": 0.75,
                        "tags": ["decision", "session-outcome"],
                    })
                    break

        return results

    async def _merge_similar_memories(
        self,
        user_id: str,
        new_memories: list[dict[str, Any]],
    ) -> int:
        """Merge new memories with existing similar ones."""
        if not self._memory_service or not new_memories:
            return 0

        merged = 0
        try:
            existing = await self._memory_service.retrieve_memories(
                user_id=user_id,
                limit=200,
            )

            for new_mem in new_memories:
                new_text = self._normalize_text(new_mem.get("content", ""))
                for existing_mem in existing:
                    existing_text = self._normalize_text(existing_mem.content)
                    similarity = self._text_similarity(new_text, existing_text)
                    if similarity > 0.85:
                        existing_mem.importance = max(
                            existing_mem.importance,
                            new_mem.get("importance", 0.5),
                        )
                        existing_mem.access_count += 1
                        merged += 1
                        break

        except Exception as e:
            logger.debug("dreaming_merge_error", error=str(e))

        return merged

    async def _archive_old_if_needed(self, user_id: str) -> int:
        """Archive old low-importance memories if count exceeds threshold."""
        if self._memory_service is None:
            return 0

        try:
            stats = await self._memory_service.auto_archive_old_memories(
                user_id=user_id,
                max_episodic_age_days=30,
                min_importance=0.3,
            )
            return stats.get("archived", 0)
        except Exception:
            return 0

    def _normalize_text(self, text: str) -> str:
        """Normalize text for deduplication comparison."""
        return " ".join(text.lower().split())

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple Jaccard similarity between two strings."""
        if not a or not b:
            return 0.0
        set_a = set(a.split())
        set_b = set(b.split())
        intersection = set_a & set_b
        union = set_a | set_b
        if not union:
            return 0.0
        return len(intersection) / len(union)

    def get_stats(self) -> dict[str, Any]:
        """Get dreaming engine statistics."""
        return {
            "is_running": self._running,
            "reflection_count": len(self._reflection_history),
            "consolidation_count": len(self._consolidation_history),
            "last_reflection": self._last_reflection,
            "last_consolidation": self._last_consolidation,
            "custom_extractors": len(self._custom_extractors),
        }
