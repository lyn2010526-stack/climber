"""Memory extraction from committed conversations.

Classification targets user preferences, project facts, and skill experience,
matching the memory schemas OpenViking derives from committed sessions. Rule
signals keep extraction deterministic and credential-free; extracted memories
land in ``episodic_memories`` (searchable) and are mirrored into the directory
semantic index scoped to the memories directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from app.core.memory_archive.index import SemanticIndex, semantic_index
from app.core.memory_archive.summarizer import _first_sentence

logger = structlog.get_logger()

MEMORY_TYPES = ("user_preference", "project_fact", "skill_experience")
MEMORY_SCOPE = "memories"

MIN_EXTRACT_LENGTH = 20
MAX_EXTRACT_LENGTH = 600

_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "user_preference",
        (
            "i prefer", "i like", "i want", "i'd like", "please remember",
            "my preference", "i usually", "prefer to", "please note",
        ),
    ),
    (
        "project_fact",
        (
            "my name is", "i work", "fact:", "key fact", "the project uses",
            "the project is", "our stack", "we use", "the repo", "the codebase",
        ),
    ),
    (
        "skill_experience",
        (
            "i learned", "worked well", "tip:", "best practice", "lesson:",
            "a useful pattern", "remember this", "works best", "i found that",
            "in my experience",
        ),
    ),
)


@dataclass
class ExtractedMemory:
    """One classified memory candidate from a conversation."""

    memory_type: str
    content: str
    importance: float = 0.6


class MemoryExtractor:
    """Classify and persist memories extracted from committed sessions."""

    def __init__(self, *, semantic: SemanticIndex | None = None, store: Any = None) -> None:
        self._semantic = semantic or semantic_index
        self._store = store

    @staticmethod
    def classify(messages: list[dict[str, Any]]) -> list[ExtractedMemory]:
        """Classify archivable messages into memory candidates.

        Each message contributes at most one memory: the first signal category
        that matches, so multi-class noise stays bounded.
        """
        extracted: list[ExtractedMemory] = []
        for message in messages:
            text = (message.get("content") or "").strip()
            if len(text) < MIN_EXTRACT_LENGTH:
                continue
            lower = text.lower()
            for memory_type, keywords in _SIGNALS:
                if any(keyword in lower for keyword in keywords):
                    extracted.append(
                        ExtractedMemory(
                            memory_type=memory_type,
                            content=_first_sentence(text, limit=MAX_EXTRACT_LENGTH),
                        )
                    )
                    break
        return extracted

    async def extract(
        self,
        user_id: str,
        session_id: str,
        messages: list[dict[str, Any]],
        *,
        agent_id: str | None = None,
    ) -> dict[str, int]:
        """Persist extracted memories and mirror them into the semantic index."""
        stats = dict.fromkeys(MEMORY_TYPES, 0)
        for item in self.classify(messages):
            if await self._store_memory(user_id, session_id, item, agent_id):
                stats[item.memory_type] += 1
        logger.info("memory_extraction_done", user_id=user_id, session_id=session_id, stats=stats)
        return stats

    async def _store_memory(
        self,
        user_id: str,
        session_id: str,
        item: ExtractedMemory,
        agent_id: str | None,
    ) -> bool:
        try:
            if self._store is None:
                from app.core.persistent_memory import persistent_memory

                self._store = persistent_memory
            memory = await self._store.create_episodic_memory(
                user_id=user_id,
                content=item.content,
                agent_id=agent_id,
                memory_type=item.memory_type,
                importance=item.importance,
                tags=["extracted", item.memory_type],
                source_session_id=session_id,
                metadata={"extracted_by": "session_memory_extractor", "scope": MEMORY_SCOPE},
            )
        except Exception as exc:
            logger.warning("memory_store_failed", memory_type=item.memory_type, error=str(exc))
            return False
        await self._semantic.index(
            memory.content,
            scope=MEMORY_SCOPE,
            level=2,
            doc_id=str(memory.id),
            user_id=user_id,
            kind="memory",
            memory_type=item.memory_type,
        )
        return True


# Global singleton
memory_extractor = MemoryExtractor()
