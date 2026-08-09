"""User settings model for agent mode and MCP control."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base


class McpStatus(str, Enum):
    """MCP process status."""

    DISCONNECTED = "disconnected"
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"
    RESTARTING = "restarting"


class UserSettings(Base):
    """User settings for agent mode and MCP control."""

    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Agent mode toggles
    autonomous_agent_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    token_throttle_mcp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # MCP status tracking
    mcp_status: Mapped[McpStatus] = mapped_column(
        SQLEnum(McpStatus), default=McpStatus.DISCONNECTED
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
