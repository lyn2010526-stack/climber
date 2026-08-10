"""Memory blocks system — reference: Letta Block Memory.

Features:
- Block-based memory: each block has label/value/read_only/limit
- Compile-time injection into system prompt
- Memory change detection and auto-rebuild
- Archival memory paging (Passage Memory)
- Cross-session entity extraction
"""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class BlockType(StrEnum):
    CORE = "core"  # Always injected, read-only
    USER = "user"  # User-managed, editable
    ARCHIVE = "archive"  # Paged archival memory
    ENTITY = "entity"  # Extracted entities
    CONTEXT = "context"  # Session-specific context
    PERSONA = "persona"  # Agent persona/identity block


@dataclass
class MemoryBlock:
    """A single memory block with metadata."""
    label: str
    value: str
    block_type: BlockType = BlockType.CORE
    read_only: bool = False
    limit: int = 5000  # Max characters
    description: str = ""
    block_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)
    metadata: dict[str, Any] = field(default_factory=dict)

    def update(self, new_value: str) -> bool:
        """Update block value. Returns False if read-only."""
        if self.read_only:
            return False
        if len(new_value) > self.limit:
            new_value = new_value[:self.limit]
        self.value = new_value
        self.updated_at = time.monotonic()
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "value": self.value,
            "block_type": self.block_type.value,
            "read_only": self.read_only,
            "limit": self.limit,
            "description": self.description,
            "updated_at": self.updated_at,
        }


@dataclass
class PassageRecord:
    """A single archival memory passage."""
    content: str
    source: str = ""  # Where this passage came from
    timestamp: float = field(default_factory=time.monotonic)
    passage_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryBlockStore:
    """Store and manage memory blocks.

    Reference: Letta Block Memory — discrete memory blocks with
    read-only protection and compile-time prompt injection.
    """

    def __init__(self) -> None:
        self._blocks: dict[str, MemoryBlock] = {}
        self._archive: list[PassageRecord] = []
        self._max_archive_size = 1000

    def add_block(self, block: MemoryBlock) -> str:
        """Add a memory block. Returns block_id."""
        self._blocks[block.label] = block
        return block.block_id

    def get_block(self, label: str) -> MemoryBlock | None:
        """Get a block by label."""
        return self._blocks.get(label)

    def update_block(self, label: str, new_value: str) -> bool:
        """Update a block's value."""
        block = self._blocks.get(label)
        if not block:
            return False
        return block.update(new_value)

    def remove_block(self, label: str) -> bool:
        """Remove a block. Cannot remove read-only blocks."""
        block = self._blocks.get(label)
        if not block or block.read_only:
            return False
        del self._blocks[label]
        return True

    def list_blocks(self, block_type: BlockType | None = None) -> list[MemoryBlock]:
        """List all blocks, optionally filtered by type."""
        blocks = list(self._blocks.values())
        if block_type:
            blocks = [b for b in blocks if b.block_type == block_type]
        return blocks

    def compile_prompt(self, include_types: list[BlockType] | None = None) -> str:
        """Compile memory blocks into system prompt section.

        Reference: Letta — blocks are injected at compile time, not runtime.
        """
        blocks = self.list_blocks()
        if include_types:
            blocks = [b for b in blocks if b.block_type in include_types]

        if not blocks:
            return ""

        sections = []
        for block in blocks:
            sections.append(f"### {block.label}\n{block.value}")

        return "\n\n".join(sections)

    def add_passage(self, content: str, source: str = "", metadata: dict[str, Any] | None = None) -> str:
        """Add a passage to archival memory."""
        passage = PassageRecord(
            content=content,
            source=source,
            metadata=metadata or {},
        )
        self._archive.append(passage)
        if len(self._archive) > self._max_archive_size:
            self._archive = self._archive[-self._max_archive_size // 2:]
        return passage.passage_id

    def search_archive(self, query: str, max_results: int = 5) -> list[PassageRecord]:
        """Simple keyword search over archival memory."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, PassageRecord]] = []

        for passage in self._archive:
            content_words = set(passage.content.lower().split())
            if not content_words:
                continue
            overlap = len(query_words & content_words)
            if overlap > 0:
                score = overlap / len(query_words) if query_words else 0
                scored.append((score, passage))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:max_results]]

    def get_stats(self) -> dict[str, Any]:
        """Get memory store statistics."""
        type_counts: dict[str, int] = {}
        for block in self._blocks.values():
            t = block.block_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_blocks": len(self._blocks),
            "type_distribution": type_counts,
            "archive_size": len(self._archive),
            "total_chars": sum(len(b.value) for b in self._blocks.values()),
        }


class EntityExtractor:
    """Extract entities from conversation for cross-session memory.

    Lightweight implementation — production systems should use NER models.
    """

    # Simple patterns for entity extraction
    PATTERNS = {
        "person": r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Full names
        "email": r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b',
        "url": r'https?://[^\s<>\"\')\]]+',
        "file_path": r'(?:[\w./\\]+/)+\.\w{2,4}',
        "date": r'\b\d{4}-\d{2}-\d{2}\b',
    }

    @classmethod
    def extract(cls, text: str) -> dict[str, list[str]]:
        """Extract entities from text."""
        entities: dict[str, list[str]] = {}
        for entity_type, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = list(set(matches))  # Deduplicate
        return entities

    @classmethod
    def extract_to_block(cls, text: str, label: str = "entities") -> MemoryBlock:
        """Extract entities and format as a memory block."""
        entities = cls.extract(text)
        lines = []
        for entity_type, values in entities.items():
            lines.append(f"- {entity_type}: {', '.join(values[:10])}")

        value = "\n".join(lines) if lines else "No entities detected."
        return MemoryBlock(
            label=label,
            value=value,
            block_type=BlockType.ENTITY,
            read_only=False,
            description="Auto-extracted entities from conversation",
        )


class MemoryConsolidator:
    """Consolidate memories across sessions.

    Reference: Letta memory consolidation — merge similar blocks,
    prune outdated information, update entity graphs.
    """

    def __init__(self, store: MemoryBlockStore) -> None:
        self._store = store

    def consolidate(self) -> dict[str, Any]:
        """Run consolidation pass on memory blocks.

        Returns:
            Report of consolidation actions taken
        """
        report: dict[str, Any] = {
            "blocks_pruned": 0,
            "blocks_merged": 0,
            "archive_indexed": 0,
        }

        # Remove empty blocks (except read-only)
        to_remove = [
            label for label, block in self._store._blocks.items()
            if not block.read_only and not block.value.strip()
        ]
        for label in to_remove:
            self._store.remove_block(label)
            report["blocks_pruned"] += 1

        # Index recent archive passages into entity block
        recent_passages = self._store._archive[-10:]
        if recent_passages:
            all_entities: dict[str, set[str]] = {}
            for passage in recent_passages:
                extracted = EntityExtractor.extract(passage.content)
                for etype, values in extracted.items():
                    if etype not in all_entities:
                        all_entities[etype] = set()
                    all_entities[etype].update(values)

            if all_entities:
                entity_block = self._store.get_block("entities")
                if entity_block and not entity_block.read_only:
                    lines = []
                    for etype, values in all_entities.items():
                        lines.append(f"- {etype}: {', '.join(list(values)[:20])}")
                    entity_block.update("\n".join(lines))
                    report["archive_indexed"] = len(recent_passages)

        logger.info("memory_consolidation.complete", **report)
        return report

    def detect_stale_blocks(self, max_age_seconds: float = 86400 * 30) -> list[str]:
        """Detect blocks that haven't been updated recently."""
        now = time.monotonic()
        stale = []
        for label, block in self._store._blocks.items():
            if block.read_only:
                continue
            age = now - block.updated_at
            if age > max_age_seconds:
                stale.append(label)
        return stale


def create_persona_block(agent_id: str, persona_data: dict) -> MemoryBlock:
    """Create a persona memory block from persona data.

    Persona blocks are persona-aware: different agents have different
    persona blocks keyed by agent_id.
    """
    lines = [f"Agent: {persona_data.get('name', 'Unknown')}"]
    if persona_data.get('role'):
        lines.append(f"Role: {persona_data['role']}")
    if persona_data.get('personality_traits'):
        lines.append(f"Traits: {', '.join(persona_data['personality_traits'])}")
    if persona_data.get('expertise'):
        lines.append(f"Expertise: {', '.join(persona_data['expertise'])}")
    if persona_data.get('communication_style'):
        lines.append(f"Style: {persona_data['communication_style']}")
    if persona_data.get('goals'):
        lines.append("Goals:")
        lines.extend(f"  - {g}" for g in persona_data['goals'])

    return MemoryBlock(
        label=f"persona_{agent_id}",
        value="\n".join(lines),
        block_type=BlockType.PERSONA,
        read_only=False,
        description=f"Persona for agent {agent_id}",
        metadata={"agent_id": agent_id, "source": "persona_system"},
    )


class PersonaAwareBlockStore:
    """Memory block store with persona awareness.

    Different agents have different persona blocks, and the store
    tracks which blocks belong to which agent.
    """

    def __init__(self) -> None:
        self._store = MemoryBlockStore()
        self._agent_blocks: dict[str, set[str]] = {}

    def add_block(self, block: MemoryBlock, agent_id: str | None = None) -> str:
        """Add a block, optionally associated with an agent."""
        block_id = self._store.add_block(block)
        if agent_id:
            if agent_id not in self._agent_blocks:
                self._agent_blocks[agent_id] = set()
            self._agent_blocks[agent_id].add(block.label)
        return block_id

    def get_block(self, label: str) -> MemoryBlock | None:
        """Get a block by label."""
        return self._store.get_block(label)

    def update_block(self, label: str, new_value: str) -> bool:
        """Update a block's value."""
        return self._store.update_block(label, new_value)

    def list_blocks(self, agent_id: str | None = None) -> list[MemoryBlock]:
        """List blocks, optionally filtered by agent_id."""
        if agent_id and agent_id in self._agent_blocks:
            labels = self._agent_blocks[agent_id]
            return [b for b in self._store.list_blocks() if b.label in labels]
        return self._store.list_blocks()

    def remove_block(self, label: str) -> bool:
        """Remove a block."""
        return self._store.remove_block(label)

    def compile_prompt(self, agent_id: str | None = None) -> str:
        """Compile blocks into prompt, optionally filtered by agent."""
        blocks = self.list_blocks(agent_id)
        if not blocks:
            return ""
        sections = []
        for block in blocks:
            sections.append(f"### {block.label}\n{block.value}")
        return "\n\n".join(sections)
