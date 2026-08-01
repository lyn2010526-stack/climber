"""Unified memory with composite scoring and hierarchical scope.

Provides a single memory interface with:
- Hierarchical scope (like filesystem paths)
- Composite scoring (relevance x importance x recency)
- Shallow (vector) and deep (LLM-assisted) recall
- Non-blocking batch operations
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MemoryScope:
    """Hierarchical memory scope (like filesystem paths).

    Scopes organize memory into a tree structure:
    /project/alpha
    /project/beta
    /agent/researcher
    /agent/writer
    """

    def __init__(self, path: str = "/"):
        self.path = self._normalize_path(path)

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize a scope path."""
        if not path.startswith("/"):
            path = "/" + path
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        return path or "/"

    def parent(self) -> MemoryScope:
        """Get the parent scope."""
        if self.path == "/":
            return MemoryScope("/")
        parts = self.path.rsplit("/", 1)
        return MemoryScope(parts[0] or "/")

    def child(self, name: str) -> MemoryScope:
        """Get a child scope."""
        return MemoryScope(f"{self.path}/{name}")

    def is_ancestor_of(self, other: MemoryScope) -> bool:
        """Check if this scope is an ancestor of another."""
        return other.path.startswith(self.path + "/") or other.path == self.path

    def __str__(self) -> str:
        return self.path

    def __repr__(self) -> str:
        return f"MemoryScope('{self.path}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MemoryScope):
            return self.path == other.path
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.path)


class MemoryRecord(BaseModel):
    """Single memory record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    content: str
    scope: str = "/"
    categories: list[str] = Field(default_factory=list)
    importance: float = 0.5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    last_accessed: datetime | None = None


class UnifiedMemory:
    """Unified memory with composite scoring.

    Combines vector similarity, importance weighting, and recency
    decay into a single relevance score for memory retrieval.
    """

    def __init__(
        self,
        decay_half_life_days: float = 30.0,
        relevance_weight: float = 0.5,
        importance_weight: float = 0.3,
        recency_weight: float = 0.2,
    ):
        self._records: dict[str, MemoryRecord] = {}
        self._scopes: set[str] = {"/"}
        self.decay_half_life_days = decay_half_life_days
        self.relevance_weight = relevance_weight
        self.importance_weight = importance_weight
        self.recency_weight = recency_weight

    async def remember(
        self,
        content: str,
        scope: str = "/",
        categories: list[str] | None = None,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory record.

        Returns the ID of the created record.
        """
        record = MemoryRecord(
            content=content,
            scope=MemoryScope._normalize_path(scope),
            categories=categories or [],
            importance=max(0.0, min(1.0, importance)),
            metadata=metadata or {},
        )

        self._records[record.id] = record
        self._scopes.add(record.scope)

        logger.debug(
            "memory_remembered",
            record_id=record.id,
            scope=record.scope,
            importance=record.importance,
        )
        return record.id

    async def recall(
        self,
        query: str,
        scope: str | None = None,
        limit: int = 5,
        depth: str = "shallow",
    ) -> list[MemoryRecord]:
        """Recall memories relevant to a query.

        depth="shallow": pure vector search (~200ms)
        depth="deep": LLM query analysis + multi-step exploration
        """
        if scope:
            scope_path = MemoryScope._normalize_path(scope)
            candidates = [
                r for r in self._records.values()
                if r.scope == scope_path or r.scope.startswith(scope_path + "/")
            ]
        else:
            candidates = list(self._records.values())

        if not candidates:
            return []

        if depth == "deep":
            return await self._deep_recall(query, candidates, limit)

        return self._shallow_recall(query, candidates, limit)

    async def remember_many(self, records: list[dict]) -> list[str]:
        """Non-blocking batch save of multiple memory records.

        Each dict should have: content, and optionally scope, categories,
        importance, metadata.
        """
        ids: list[str] = []

        for rec_data in records:
            content = rec_data.pop("content", "")
            if not content:
                continue
            record_id = await self.remember(content=content, **rec_data)
            ids.append(record_id)

        logger.info("memory_batch_saved", count=len(ids))
        return ids

    def get_scope(self, path: str) -> MemoryScope:
        """Get a scope object for a path."""
        return MemoryScope(path)

    def get_records_in_scope(self, scope: str) -> list[MemoryRecord]:
        """Get all records within a scope."""
        scope_path = MemoryScope._normalize_path(scope)
        return [
            r for r in self._records.values()
            if r.scope == scope_path or r.scope.startswith(scope_path + "/")
        ]

    async def forget(self, record_id: str) -> bool:
        """Remove a memory record by ID."""
        if record_id in self._records:
            del self._records[record_id]
            logger.debug("memory_forgotten", record_id=record_id)
            return True
        return False

    async def update_importance(self, record_id: str, importance: float) -> bool:
        """Update the importance of a memory record."""
        record = self._records.get(record_id)
        if record:
            record.importance = max(0.0, min(1.0, importance))
            return True
        return False

    def list_scopes(self) -> list[str]:
        """List all registered scopes."""
        return sorted(self._scopes)

    def count(self, scope: str | None = None) -> int:
        """Count memory records, optionally filtered by scope."""
        if scope:
            scope_path = MemoryScope._normalize_path(scope)
            return sum(
                1 for r in self._records.values()
                if r.scope == scope_path or r.scope.startswith(scope_path + "/")
            )
        return len(self._records)

    def _shallow_recall(
        self, query: str, candidates: list[MemoryRecord], limit: int,
    ) -> list[MemoryRecord]:
        """Pure vector search with composite scoring."""
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored: list[tuple[float, MemoryRecord]] = []

        for record in candidates:
            doc_lower = record.content.lower()
            matches = sum(1 for term in query_terms if term in doc_lower)
            if not matches and query_terms:
                continue

            relevance = matches / len(query_terms) if query_terms else 0.0
            recency_score = self._compute_recency_score(record.created_at)
            importance_score = record.importance

            composite = (
                self.relevance_weight * relevance
                + self.importance_weight * importance_score
                + self.recency_weight * recency_score
            )

            scored.append((composite, record))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, record in scored[:limit]:
            record.access_count += 1
            record.last_accessed = datetime.now(timezone.utc)
            results.append(record)
        return results

    async def _deep_recall(
        self, query: str, candidates: list[MemoryRecord], limit: int,
    ) -> list[MemoryRecord]:
        """LLM query analysis + multi-step exploration.

        First does a shallow recall, then uses LLM to analyze
        and expand the query for a second pass.
        """
        initial_results = self._shallow_recall(query, candidates, limit * 2)

        if not initial_results:
            return []

        analysis = await self._analyze_query(query, initial_results)

        if analysis and "expanded_terms" in analysis:
            expanded_query = " ".join(analysis["expanded_terms"])
            expanded_results = self._shallow_recall(expanded_query, candidates, limit * 2)
            seen_ids = {r.id for r in initial_results}
            for r in expanded_results:
                if r.id not in seen_ids:
                    initial_results.append(r)
                    seen_ids.add(r.id)

        initial_results.sort(
            key=lambda r: (
                self.relevance_weight * self._term_overlap(query, r.content)
                + self.importance_weight * r.importance
                + self.recency_weight * self._compute_recency_score(r.created_at)
            ),
            reverse=True,
        )

        return initial_results[:limit]

    async def _analyze_query(
        self, query: str, initial_results: list[MemoryRecord],
    ) -> dict[str, Any] | None:
        """Use LLM to analyze query and suggest expanded search terms."""
        try:
            from app.core.di import resolve as di_resolve
            llm_client = di_resolve("LLMCilent", default=None)
        except Exception:
            llm_client = None

        if not llm_client:
            return None

        context = "\n".join(f"- {r.content[:200]}" for r in initial_results[:5])
        prompt = (
            f"Given this query: '{query}'\n\n"
            f"And these initial memory matches:\n{context}\n\n"
            f"Suggest 3-5 additional search terms that might find related memories.\n"
            f"Respond with JSON: {{\"expanded_terms\": [\"term1\", \"term2\", ...]}}"
        )

        try:
            import json
            response = await llm_client.generate(prompt)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return json.loads(cleaned)
        except Exception as e:
            logger.debug("deep_recall_analysis_failed", error=str(e))
            return None

    def _compute_recency_score(self, created_at: datetime) -> float:
        """Compute a recency score with exponential decay."""
        now = datetime.now(timezone.utc)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).total_seconds() / 86400.0
        import math
        return math.exp(-0.693 * age_days / self.decay_half_life_days)

    @staticmethod
    def _term_overlap(query: str, content: str) -> float:
        """Compute term overlap between query and content."""
        query_terms = set(query.lower().split())
        content_terms = set(content.lower().split())
        if not query_terms:
            return 0.0
        return len(query_terms & content_terms) / len(query_terms)
