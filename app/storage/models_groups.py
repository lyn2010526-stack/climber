"""Group data models for multi-agent collaboration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage import Base


class AgentGroup(Base):
    """A group of agents that can collaborate on tasks."""

    __tablename__ = "agent_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, default="default-user")

    # Group config
    topic: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, paused, archived
    max_rounds: Mapped[int] = mapped_column(Integer, default=10)

    # Process type and manager config
    process_type: Mapped[str] = mapped_column(String(20), server_default="sequential")  # sequential, hierarchical, group_chat
    manager_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    manager_llm: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "openai/gpt-4o"

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    members: Mapped[list[AgentGroupMember]] = relationship(back_populates="group", cascade="all, delete-orphan", foreign_keys="[AgentGroupMember.group_id]", primaryjoin="AgentGroup.id == AgentGroupMember.group_id")
    messages: Mapped[list[AgentGroupMessage]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="AgentGroupMessage.created_at")
    tasks: Mapped[list[AgentGroupTask]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="AgentGroupTask.created_at.desc()")
    memories: Mapped[list[AgentGroupMemory]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="AgentGroupMemory.created_at.desc()")
    checkpoints: Mapped[list[AgentGroupTaskCheckpoint]] = relationship(back_populates="group", cascade="all, delete-orphan", order_by="AgentGroupTaskCheckpoint.created_at.desc()")


class AgentGroupMember(Base):
    """Member (agent) belonging to a group."""

    __tablename__ = "agent_group_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Role in the group
    role: Mapped[str] = mapped_column(String(50), default="participant")  # worker, reviewer, moderator, observer, manager
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, idle, left, error
    is_speaking: Mapped[bool] = mapped_column(Boolean, default=False)

    # Collaboration config (auto loop)
    model_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # openai/anthropic/google/ollama
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_type: Mapped[str] = mapped_column(String(20), default="code")  # code, architecture, security
    is_worker: Mapped[bool] = mapped_column(Boolean, default=False)

    # Stats
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    group: Mapped[AgentGroup] = relationship(back_populates="members")


class AgentGroupMessage(Base):
    """Message sent within a group chat."""

    __tablename__ = "agent_group_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=True)  # None for system messages
    sender_name: Mapped[str] = mapped_column(String(100), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="text")  # text, system, vote, proposal
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    group: Mapped[AgentGroup] = relationship(back_populates="messages")


class AgentGroupTask(Base):
    """Auto collaboration task record."""

    __tablename__ = "agent_group_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Task config
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, paused, completed, failed, partial, stopped, awaiting_human_review
    worker_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_group_members.id"), nullable=True)
    reviewer_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    current_round: Mapped[int] = mapped_column(Integer, default=0)

    # Task dependencies and context passing
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)  # task IDs that must complete before this task runs
    context: Mapped[list[str]] = mapped_column(JSON, default=list)  # list of task IDs whose output should be passed as context
    parent_task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_group_tasks.id"), nullable=True)

    # Guardrails and validation
    guardrails: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # list of guardrail configs

    # Human-in-the-loop
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, approved, rejected
    human_review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured output schema
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # JSON schema for output validation

    # Result
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    structured_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # parsed structured output
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Execution lease (crash recovery + fencing)
    lease_owner: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    lease_token: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Callbacks
    step_callback: Mapped[str | None] = mapped_column(String(255), nullable=True)  # reference to callback function
    task_callback: Mapped[str | None] = mapped_column(String(255), nullable=True)  # reference to callback function

    # Relationships
    group: Mapped[AgentGroup] = relationship(back_populates="tasks")
    checkpoints: Mapped[list[AgentGroupTaskCheckpoint]] = relationship(back_populates="task", cascade="all, delete-orphan")
    child_tasks: Mapped[list[AgentGroupTask]] = relationship("AgentGroupTask", foreign_keys="AgentGroupTask.parent_task_id", back_populates="parent_task")
    parent_task: Mapped[AgentGroupTask | None] = relationship("AgentGroupTask", remote_side="AgentGroupTask.id", back_populates="child_tasks")


class AgentGroupTaskCheckpoint(Base):
    """Checkpoint for task execution state, enabling resume after interruption."""

    __tablename__ = "agent_group_task_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_group_tasks.id"), nullable=False, index=True)

    # Checkpoint state
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, paused, completed, failed, stopped
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Full state snapshot
    history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    current_artifact: Mapped[str] = mapped_column(Text, default="")
    all_issues: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # Member configs for resumption
    worker_config: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewer_configs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    manager_config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Task description and context
    task_description: Mapped[str] = mapped_column(Text, default="")
    context_data: Mapped[dict] = mapped_column(JSON, default=dict)  # outputs from dependent tasks

    # Structured output state
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    structured_output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Human review state
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    human_review_status: Mapped[str] = mapped_column(String(20), default="pending")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    group: Mapped[AgentGroup] = relationship(back_populates="checkpoints")
    task: Mapped[AgentGroupTask] = relationship(back_populates="checkpoints")


class AgentGroupMemory(Base):
    """Short-term and long-term memory for agent groups."""

    __tablename__ = "agent_group_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_group_tasks.id"), nullable=True, index=True)

    # Memory classification
    memory_type: Mapped[str] = mapped_column(String(30), default="short_term")  # short_term, long_term, insight
    memory_category: Mapped[str] = mapped_column(String(30), default="conversation")  # conversation, decision, fact, lesson

    # Memory content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    # Scoring for retrieval
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    recency_score: Mapped[float] = mapped_column(Float, default=1.0)
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    # Source tracking
    source_agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    group: Mapped[AgentGroup] = relationship(back_populates="memories")


class AgentGroupGuardrail(Base):
    """Guardrail configuration for task validation."""

    __tablename__ = "agent_group_guardrails"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_groups.id"), nullable=False, index=True)
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("agent_group_tasks.id"), nullable=True, index=True)

    # Guardrail config
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    guardrail_type: Mapped[str] = mapped_column(String(20), default="llm")  # llm, function, schema

    # Validation config
    validation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # for LLM-based guardrails
    validation_function: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Python dotted path for function-based
    schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # JSON schema for output validation

    # Retry config
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    retry_prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    pass_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# Add relationship to AgentGroup (after both classes are defined)
