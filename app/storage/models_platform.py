"""Database models for workflows, crews, plugins, skills, traces and clusters.

These back the API endpoints that previously returned stub data.
Kept intentionally close in style to app/storage/database.py.
"""

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
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class Workflow(Base):
    """A user-defined DAG workflow (nodes/edges from the React Flow editor)."""

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled Workflow")
    description: Mapped[str] = mapped_column(Text, default="")
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    last_status: Mapped[str] = mapped_column(String(20), default="never_run")
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkflowRun(Base):
    """A single execution record of a workflow."""

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    node_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Crew(Base):
    """A multi-agent crew definition."""

    __tablename__ = "crews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    process: Mapped[str] = mapped_column(String(20), default="sequential")  # sequential / hierarchical
    agents: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    tasks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrewRun(Base):
    """Execution record of a crew run."""

    __tablename__ = "crew_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    crew_id: Mapped[str] = mapped_column(String(36), ForeignKey("crews.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output: Mapped[str] = mapped_column(Text, default="")
    task_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Skill(Base):
    """A reusable skill (prompt template + tool bundle).

    """

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    prompt_template: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Three-tier scope
    scope: Mapped[str] = mapped_column(String(20), default="global")  # global / team / user
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_force_delivery: Mapped[bool] = mapped_column(Boolean, default=False)
    is_orphan: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    active_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    admin_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_tags: Mapped[list[str]] = mapped_column(JSON, default=list)


class Trace(Base):
    """An execution trace span for observability."""

    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default-user")
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trace_type: Mapped[str] = mapped_column(String(30), default="agent_run")
    name: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(20), default="ok")
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    spans: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Cluster(Base):
    """A worker node in the local cluster."""

    __tablename__ = "cluster_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[str] = mapped_column(String(20), default="worker")
    status: Mapped[str] = mapped_column(String(20), default="offline")
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DocumentChunk(Base):
    """A persisted chunk of an indexed document, enabling real retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    collection: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AutoLoopTask(Base):
    """Persisted autonomous task for AutoLoopEngine."""

    __tablename__ = "auto_loop_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=10)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
