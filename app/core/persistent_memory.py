"""Persistent memory service — MemGPT/Letta-style memory management.

Provides:
- Episodic memory storage, retrieval, and summarization
- Knowledge graph construction and querying
- User profile management
- Automatic memory extraction from conversations
- Relevance-based memory retrieval with scoring
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import and_, desc, func, select

from app.core.vector_memory import vector_memory
from app.storage import async_session
from app.storage.models_memory import (
    ArchivalPassage,
    EpisodicMemory,
    KnowledgeGraph,
    MemoryRetrievalLog,
    UserProfile,
)

logger = structlog.get_logger()


class PersistentMemoryService:
    """Service layer for persistent agent memory operations.

    Replaces the in-memory LongTermMemory with PostgreSQL-backed
    persistent storage that survives server restarts.
    """

    # ─── Episodic Memory ────────────────────────────────────────────────

    async def create_episodic_memory(
        self,
        user_id: str,
        content: str,
        agent_id: str | None = None,
        memory_type: str = "conversation",
        importance: float = 0.5,
        tags: list[str] | None = None,
        source_session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodicMemory:
        """Store a new episodic memory."""
        async with async_session() as db:
            memory = EpisodicMemory(
                user_id=user_id,
                content=content,
                summary=content[:200],
                agent_id=agent_id,
                memory_type=memory_type,
                importance=importance,
                tags=tags or [],
                source_session_id=source_session_id,
                metadata_=metadata or {},
            )
            db.add(memory)
            await db.commit()
            await db.refresh(memory)
            return memory

    async def retrieve_memories(
        self,
        user_id: str,
        query: str = "",
        limit: int = 10,
        min_importance: float = 0.0,
        session_id: str | None = None,
    ) -> list[EpisodicMemory]:
        """Retrieve relevant memories for a user.

        Uses vector similarity search when available, falls back to keyword search.
        """
        async with async_session() as db:
            if query:
                try:
                    vector_results = await vector_memory.search(
                        collection="episodic",
                        query=query,
                        top_k=limit * 3,
                        where={"user_id": user_id},
                    )
                except Exception:
                    vector_results = []

                if vector_results:
                    vector_ids = [r["id"] for r in vector_results]
                    result = await db.execute(
                        select(EpisodicMemory)
                        .where(
                            and_(
                                EpisodicMemory.user_id == user_id,
                                EpisodicMemory.id.in_(vector_ids),
                                EpisodicMemory.importance >= min_importance,
                            )
                        )
                    )
                    memory_map = {m.id: m for m in result.scalars().all()}
                    ordered = []
                    for vid in vector_ids:
                        if vid in memory_map:
                            mem = memory_map[vid]
                            mem.access_count += 1
                            mem.last_accessed_at = datetime.now(UTC)
                            ordered.append(mem)
                    for mem in ordered[:limit]:
                        log = MemoryRetrievalLog(
                            memory_id=mem.id,
                            user_id=user_id,
                            session_id=session_id,
                            retrieval_query=query[:500],
                        )
                        db.add(log)
                    await db.commit()
                    return ordered[:limit]

            # Fallback: keyword search
            result = await db.execute(
                select(EpisodicMemory)
                .where(
                    and_(
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.importance >= min_importance,
                    )
                )
                .order_by(
                    desc(EpisodicMemory.importance * EpisodicMemory.recency_score),
                )
                .limit(limit * 3)
            )
            memories = list(result.scalars().all())

            if query:
                query_lower = query.lower()
                scored = []
                for mem in memories:
                    score = mem.importance * mem.recency_score
                    content_lower = mem.content.lower()
                    if any(word in content_lower for word in query_lower.split() if len(word) > 3):
                        score *= 1.5
                        mem.access_count += 1
                        mem.last_accessed_at = datetime.now(UTC)
                    scored.append((score, mem))

                scored.sort(key=lambda x: x[0], reverse=True)
                result_memories = [m for _, m in scored[:limit]]
            else:
                result_memories = memories[:limit]

            for mem in result_memories:
                log = MemoryRetrievalLog(
                    memory_id=mem.id,
                    user_id=user_id,
                    session_id=session_id,
                    retrieval_query=query[:500],
                )
                db.add(log)

            await db.commit()
            return result_memories

    async def format_memories_for_prompt(
        self,
        user_id: str,
        query: str = "",
        max_memories: int = 5,
    ) -> str:
        """Format memories for injection into system prompt."""
        memories = await self.retrieve_memories(user_id, query=query, limit=max_memories)
        if not memories:
            return ""

        lines = ["## Relevant Memories:"]
        for mem in memories:
            lines.append(f"- [{mem.memory_type}] {mem.content}")
        return "\n".join(lines)

    async def decay_recency_scores(self, decay_factor: float = 0.95) -> int:
        """Apply time-based decay to all recency scores.

        Should be called periodically (e.g., daily via scheduler).
        Memories that aren't accessed lose relevance over time.
        """
        async with async_session() as db:
            result = await db.execute(select(EpisodicMemory))
            memories = result.scalars().all()
            for mem in memories:
                mem.recency_score *= decay_factor
            await db.commit()
            return len(memories)

    async def cleanup_old_memories(
        self,
        user_id: str,
        keep_count: int = 200,
        min_score: float = 0.01,
    ) -> int:
        """Remove low-scoring memories to prevent unbounded growth."""
        async with async_session() as db:
            # Get count
            result = await db.execute(
                select(func.count()).where(EpisodicMemory.user_id == user_id)
            )
            count = result.scalar() or 0

            if count <= keep_count:
                return 0

            # Delete lowest-scoring memories above the keep threshold
            result = await db.execute(
                select(EpisodicMemory)
                .where(EpisodicMemory.user_id == user_id)
                .where(EpisodicMemory.recency_score < min_score)
                .order_by(EpisodicMemory.importance * EpisodicMemory.recency_score)
                .limit(count - keep_count)
            )
            to_delete = result.scalars().all()
            for mem in to_delete:
                await db.delete(mem)

            await db.commit()
            return len(to_delete)

    async def auto_archive_old_memories(
        self,
        user_id: str,
        max_episodic_age_days: int = 30,
        min_importance: float = 0.3,
        batch_size: int = 50,
    ) -> dict[str, int]:
        """Move old low-importance episodic memories to archival with embeddings.

        Returns stats: {"archived": N, "skipped": N, "failed": N}
        """
        stats: dict[str, int] = {"archived": 0, "skipped": 0, "failed": 0}
        async with async_session() as db:
            cutoff = datetime.now(UTC).timestamp() - (max_episodic_age_days * 86400)
            result = await db.execute(
                select(EpisodicMemory)
                .where(
                    and_(
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.importance < min_importance,
                        EpisodicMemory.created_at < datetime.fromtimestamp(cutoff, tz=UTC),
                    )
                )
                .limit(batch_size)
            )
            old_memories = result.scalars().all()

            for mem in old_memories:
                try:
                    archive_id = f"auto-{datetime.now(UTC).strftime('%Y-%m-%d')}"
                    await self.create_archival_passage(
                        user_id=user_id,
                        text=mem.content,
                        archive_id=archive_id,
                        tags=mem.tags,
                        metadata=mem.metadata_,
                    )
                    await vector_memory.add(
                        collection="archival",
                        doc_id=f"archival-{mem.id}",
                        text=mem.content,
                        metadata={
                            "user_id": user_id,
                            "archive_id": archive_id,
                            "source": "auto_archive",
                            "original_importance": mem.importance,
                            "tags": mem.tags or [],
                        },
                    )
                    await db.delete(mem)
                    stats["archived"] += 1
                except Exception:
                    stats["failed"] += 1

            await db.commit()
            return stats

    # ─── Knowledge Graph ─────────────────────────────────────────────────

    async def add_triple(
        self,
        user_id: str,
        subject: str,
        predicate: str,
        object_: str,
        confidence: float = 0.8,
        context: str = "",
        source: str = "conversation",
    ) -> KnowledgeGraph:
        """Add a knowledge graph triple."""
        async with async_session() as db:
            # Check for existing triple
            result = await db.execute(
                select(KnowledgeGraph).where(
                    and_(
                        KnowledgeGraph.user_id == user_id,
                        KnowledgeGraph.subject == subject,
                        KnowledgeGraph.predicate == predicate,
                        KnowledgeGraph.object_ == object_,
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.confidence = max(existing.confidence, confidence)
                existing.updated_at = datetime.now(UTC)
                await db.commit()
                return existing

            triple = KnowledgeGraph(
                user_id=user_id,
                subject=subject,
                predicate=predicate,
                object_=object_,
                confidence=confidence,
                source=source,
                context=context,
            )
            db.add(triple)
            await db.commit()
            await db.refresh(triple)
            return triple

    async def query_graph(
        self,
        user_id: str,
        subject: str | None = None,
        predicate: str | None = None,
        object_: str | None = None,
        limit: int = 20,
    ) -> list[KnowledgeGraph]:
        """Query knowledge graph with optional filters."""
        async with async_session() as db:
            query = select(KnowledgeGraph).where(KnowledgeGraph.user_id == user_id)

            if subject:
                query = query.where(KnowledgeGraph.subject == subject)
            if predicate:
                query = query.where(KnowledgeGraph.predicate == predicate)
            if object_:
                query = query.where(KnowledgeGraph.object_ == object_)

            query = query.order_by(desc(KnowledgeGraph.confidence)).limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_entity_relations(
        self,
        user_id: str,
        entity: str,
        limit: int = 10,
    ) -> list[KnowledgeGraph]:
        """Get all relations for a specific entity (both as subject and object)."""
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeGraph).where(
                    and_(
                        KnowledgeGraph.user_id == user_id,
                        KnowledgeGraph.subject == entity,
                    )
                ).order_by(desc(KnowledgeGraph.confidence)).limit(limit)
            )
            return list(result.scalars().all())

    async def format_graph_for_prompt(
        self,
        user_id: str,
        entity: str,
        limit: int = 10,
    ) -> str:
        """Format knowledge graph relations for prompt injection."""
        relations = await self.get_entity_relations(user_id, entity, limit=limit)
        if not relations:
            return ""

        lines = [f"## Knowledge about \"{entity}\":"]
        for r in relations:
            lines.append(f"- {r.subject} -[{r.predicate}]-> {r.object_}")
        return "\n".join(lines)

    # ─── User Profile ────────────────────────────────────────────────────

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create a new one."""
        async with async_session() as db:
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.add(profile)
                await db.commit()
                await db.refresh(profile)
            return profile

    async def add_user_fact(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
        confidence: float = 0.8,
    ) -> UserProfile:
        """Add a persistent fact about the user."""
        profile = await self.get_or_create_profile(user_id)
        profile.facts.append({
            "category": category,
            "content": fact,
            "confidence": confidence,
            "added_at": datetime.now(UTC).isoformat(),
        })
        # Keep facts list manageable
        if len(profile.facts) > 100:
            profile.facts = profile.facts[-100:]

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()
            return profile

    async def update_preferences(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> UserProfile:
        """Update user preferences."""
        profile = await self.get_or_create_profile(user_id)
        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()
            return profile

    async def record_interaction(
        self,
        user_id: str,
        message_count: int = 1,
    ) -> None:
        """Record a user interaction for behavioral tracking."""
        profile = await self.get_or_create_profile(user_id)
        now = datetime.now(UTC)
        profile.total_sessions += 1
        profile.total_messages += message_count
        profile.last_interaction = now
        if not profile.first_interaction:
            profile.first_interaction = now

        async with async_session() as db:
            await db.merge(profile)
            await db.commit()

    async def format_profile_for_prompt(self, user_id: str) -> str:
        """Format user profile for system prompt injection."""
        profile = await self.get_or_create_profile(user_id)
        lines: list[str] = []

        # Inviolable rules (highest priority)
        if profile.inviolable:
            lines.append("[INVIOLABLE RULES — MUST FOLLOW]")
            for rule in profile.inviolable:
                lines.append(f"- {rule}")
            lines.append("")

        # User values
        if profile.values:
            lines.append("## User Values")
            for v in profile.values:
                lines.append(f"- {v}")
            lines.append("")

        # User principles
        if profile.principles:
            lines.append("## User Principles")
            for p in profile.principles:
                lines.append(f"- {p}")
            lines.append("")

        facts = profile.facts[-10:]  # Last 10 facts
        if facts:
            lines.append("## User Information:")
            for f in facts:
                lines.append(f"- [{f.get('category', 'general')}] {f.get('content', '')}")

        if profile.preferred_model:
            lines.append(f"- Preferred model: {profile.preferred_model}")
        if profile.preferred_language:
            lines.append(f"- Preferred language: {profile.preferred_language}")

        return "\n".join(lines) if lines else ""

    # ─── Auto-Extraction ─────────────────────────────────────────────────

    async def auto_extract_from_session(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, str]],
        agent_id: str | None = None,
    ) -> dict[str, int]:
        """Extract memories and knowledge from a completed conversation.

        Uses simple heuristics. In production, this would use an LLM
        to extract structured memories from the conversation.
        """
        stats = {"memories": 0, "facts": 0, "triples": 0}

        # Extract key decisions and preferences
        for msg in messages:
            content = msg.get("content", "")
            if not content or len(content) < 20:
                continue

            # Simple heuristic: messages containing "I prefer", "I like", "remember"
            lower = content.lower()
            if any(signal in lower for signal in ["i prefer", "i like", "i want", "remember that", "my name is", "i work"]):
                await self.create_episodic_memory(
                    user_id=user_id,
                    content=content[:500],
                    agent_id=agent_id,
                    memory_type="preference",
                    importance=0.7,
                    source_session_id=session_id,
                )
                stats["memories"] += 1

                # Extract as user fact
                if "my name is" in lower:
                    name_part = content[lower.index("my name is") + 11:].strip().split()[0:3]
                    name = " ".join(name_part).strip(".,!?")
                    if name:
                        await self.add_user_fact(user_id, f"Name: {name}", "personal", 0.9)
                        stats["facts"] += 1

                elif "i work" in lower:
                    work_part = content[lower.index("i work") + 7:].strip()[:100]
                    if work_part:
                        await self.add_user_fact(user_id, f"Work: {work_part}", "work", 0.8)
                        stats["facts"] += 1

        return stats

    # ─── Archival Memory ──────────────────────────────────────────────────────

    async def create_archival_passage(
        self,
        user_id: str,
        text: str,
        archive_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
    ) -> ArchivalPassage:
        """Store a new archival passage."""
        async with async_session() as db:
            passage = ArchivalPassage(
                user_id=user_id,
                text=text,
                archive_id=archive_id,
                tags=tags or [],
                metadata_=metadata or {},
                embedding=embedding,
            )
            db.add(passage)
            await db.commit()
            await db.refresh(passage)
            return passage

    async def search_archival_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        archive_id: str | None = None,
    ) -> list[ArchivalPassage]:
        """Search archival memories by semantic similarity.

        Uses vector search when available, falls back to LIKE search.
        """
        async with async_session() as db:
            if query:
                try:
                    vector_results = await vector_memory.search(
                        collection="archival",
                        query=query,
                        top_k=limit,
                        where={"user_id": user_id},
                    )
                except Exception:
                    vector_results = []

                if vector_results:
                    vector_ids = [r["id"] for r in vector_results]
                    base_query = select(ArchivalPassage).where(
                        ArchivalPassage.user_id == user_id,
                        ArchivalPassage.id.in_(vector_ids),
                    )
                    if archive_id:
                        base_query = base_query.where(ArchivalPassage.archive_id == archive_id)
                    result = await db.execute(base_query)
                    passage_map = {p.id: p for p in result.scalars().all()}
                    ordered = []
                    for vid in vector_ids:
                        if vid in passage_map:
                            passage = passage_map[vid]
                            passage.access_count += 1
                            passage.last_accessed_at = datetime.now(UTC)
                            ordered.append(passage)
                    for p in ordered:
                        await vector_memory.update_access("archival", p.id)
                    await db.commit()
                    return ordered[:limit]

            # Fallback: LIKE search
            base_query = select(ArchivalPassage).where(ArchivalPassage.user_id == user_id)
            if archive_id:
                base_query = base_query.where(ArchivalPassage.archive_id == archive_id)
            if query:
                base_query = base_query.where(ArchivalPassage.text.ilike(f"%{query}%"))
            base_query = base_query.order_by(ArchivalPassage.access_count.desc(), ArchivalPassage.created_at.desc()).limit(limit)
            result = await db.execute(base_query)
            return list(result.scalars().all())

    async def get_archival_by_tags(
        self,
        user_id: str,
        tags: list[str],
        limit: int = 20,
    ) -> list[ArchivalPassage]:
        """Get archival passages matching any of the given tags."""
        async with async_session() as db:
            query = select(ArchivalPassage).where(ArchivalPassage.user_id == user_id)
            for tag in tags:
                query = query.where(ArchivalPassage.tags.contains([tag]))
            query = query.limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def decay_recency_by_access(self) -> int:
        """Decay recency scores based on days since last access.

        Formula: recency_score = 1.0 / (1.0 + days_since_access)
        """
        async with async_session() as db:
            result = await db.execute(select(EpisodicMemory))
            memories = result.scalars().all()
            now = datetime.now(UTC)
            updated = 0
            for mem in memories:
                if mem.last_accessed_at:
                    days = (now - mem.last_accessed_at.replace(tzinfo=UTC)).days
                    mem.recency_score = 1.0 / (1.0 + days)
                    updated += 1
            await db.commit()
            return updated


# Global singleton
persistent_memory = PersistentMemoryService()
