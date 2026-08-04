"""Plugin and MCP server database models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class PluginRecord(Base):
    """Tracks installed plugins (skills, MCP servers, prompt templates)."""

    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plugin_key: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # skill | mcp | prompt
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # builtin | marketplace | custom
    source_url: Mapped[str] = mapped_column(Text, nullable=True)  # GitHub URL or npm package
    author: Mapped[str] = mapped_column(String(100), default="")
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="disabled")  # installed | enabled | disabled | error
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(10), default="")
    category: Mapped[str] = mapped_column(String(50), default="")
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    installed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MCPServerRecord(Base):
    """Tracks MCP server instances and their connection state.

    """

    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    plugin_id: Mapped[str] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    args: Mapped[list[str]] = mapped_column(JSON, default=list)
    env: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="stopped")  # stopped | connecting | connected | error
    tools_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tools: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
