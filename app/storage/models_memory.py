"""Persistent memory models — MemGPT/Letta-style layered memory.

Three layers:
1. Episodic Memory: conversation summaries and key events (like human episodic memory)
2. Knowledge Graph: entity-relation-entity triples extracted from conversations
3. User Profile: persistent user preferences, facts, and behavioral patterns
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage import Base


class EpisodicMemory(Base):
    """Conversation summaries and key events — like human episodic memory.

    Each record represents a distilled memory from a conversation session.
    Memories are ranked by importance and recency for retrieval.
    """

    __tablename__ = "episodic_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, index=True)

    # Memory content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Memory classification
    memory_type: Mapped[str] = mapped_column(String(30), default="conversation")
    # conversation, decision, preference, fact, event, task_result

    # Scoring for retrieval importance
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    recency_score: Mapped[float] = mapped_column(Float, default=1.0)  # decays over time
    access_count: Mapped[int] = mapped_column(Integer, default=0)  # how often retrieved

    # Source tracking
    source_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_message_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="episodic_memories")


class KnowledgeGraph(Base):
    """Entity-Relation-Entity triples extracted from conversations.

    Enables structured reasoning about entities mentioned across sessions.
    Example: (Alice) -[works_at]-> (Google), (Alice) -[knows]-> (Python)
    """

    __tablename__ = "knowledge_graph"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Triple components
    subject: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_: Mapped[str] = mapped_column("object", String(200), nullable=False, index=True)

    # Confidence and provenance
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    source: Mapped[str] = mapped_column(String(50), default="conversation")  # conversation, user_stated, inferred
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    context: Mapped[str] = mapped_column(Text, default="")  # original sentence/context
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class UserProfile(Base):
    """Persistent user profile — preferences, facts, behavioral patterns.

    Survives across all sessions. Built up over time from conversations.
    """

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Structured preferences
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    preferred_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Freeform facts about the user (persistent across all sessions)
    facts: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # Each fact: {"category": "work", "content": "Software engineer at Google", "confidence": 0.9}

    # Behavioral patterns
    common_topics: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # Each: {"topic": "Python", "frequency": 15, "last_mentioned": "2024-01-15"}

    # Interaction summary
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    first_interaction: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_interaction: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="profile")


class MemoryRetrievalLog(Base):
    """Log of memory retrievals for analytics and debugging.

    Tracks which memories are accessed and how often, enabling:
    - Recency score decay calculation
    - Importance score adjustment
    - Memory cleanup of never-accessed entries
    """

    __tablename__ = "memory_retrieval_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    memory_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Retrieval context
    retrieval_query: Mapped[str] = mapped_column(Text, default="")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    was_useful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # feedback signal

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CoreMemoryBlock(Base):
    """Core memory block — injected directly into system prompt.

    """

    __tablename__ = "core_memory_blocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True, index=True)

    label: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "persona", "user_profile"
    value: Mapped[str] = mapped_column(Text, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, default=4096)
    description: Mapped[str] = mapped_column(Text, default="")
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ArchivalPassage(Base):
    """Long-term archival memory with optional embedding for vector search.

    """

    __tablename__ = "archival_passages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    archive_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Persistent audit log for all agent operations.

    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False)  # file:read, command:execute, api:call, permission:*
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info / warning / critical
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)




