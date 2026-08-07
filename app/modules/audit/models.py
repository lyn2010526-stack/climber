"""Audit logging data models.

This module defines data models for comprehensive audit logging including
audit events, API call logs, and data change history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class AuditEventType(StrEnum):
    """Types of audit events."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    API_CALL = "api_call"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    SETTINGS_CHANGE = "settings_change"
    BILLING_EVENT = "billing_event"
    SECURITY_EVENT = "security_event"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"
    WORKFLOW_ACTION = "workflow_action"


class AuditSeverity(StrEnum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class AuditLog(Base):
    """Comprehensive audit log entry.

    Records all significant actions and events in the system for
    security, compliance, and debugging purposes.

    Attributes:
        id: Unique log entry identifier.
        event_type: Type of event.
        severity: Event severity level.
        user_id: User who performed the action.
        user_email: User email at time of event.
        resource_type: Type of resource affected.
        resource_id: ID of affected resource.
        action: Action performed.
        description: Human-readable description.
        before_state: State before the change.
        after_state: State after the change.
        ip_address: Source IP address.
        user_agent: Client user agent.
        request_id: Associated request ID.
        session_id: Associated session ID.
        metadata_json: Additional metadata.
        created_at: Event timestamp.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_severity", "severity"),
        Index("ix_audit_events_ip_address", "ip_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[AuditEventType] = mapped_column(SAEnum(AuditEventType), nullable=False)
    severity: Mapped[AuditSeverity] = mapped_column(SAEnum(AuditSeverity), default=AuditSeverity.INFO, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ApiCallLog(Base):
    """Log of API calls for monitoring and debugging.

    Attributes:
        id: Unique log identifier.
        request_id: Request correlation ID.
        user_id: Authenticated user ID.
        method: HTTP method.
        path: Request path.
        query_params: Query parameters.
        request_body: Request body (truncated).
        response_status: HTTP status code.
        response_body: Response body (truncated).
        duration_ms: Request duration in milliseconds.
        ip_address: Client IP address.
        user_agent: Client user agent.
        created_at: Request timestamp.
    """

    __tablename__ = "api_call_logs"
    __table_args__ = (
        Index("ix_api_call_logs_user_id", "user_id"),
        Index("ix_api_call_logs_path", "path"),
        Index("ix_api_call_logs_created_at", "created_at"),
        Index("ix_api_call_logs_status", "response_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataChangeHistory(Base):
    """Track changes to important data entities.

    Provides a detailed history of data modifications for compliance
    and rollback purposes.

    Attributes:
        id: Unique history identifier.
        entity_type: Type of entity changed.
        entity_id: ID of changed entity.
        field_name: Name of changed field.
        old_value: Previous value.
        new_value: New value.
        changed_by: User who made the change.
        change_reason: Reason for the change.
        created_at: Change timestamp.
    """

    __tablename__ = "data_change_history"
    __table_args__ = (
        Index("ix_data_change_history_entity", "entity_type", "entity_id"),
        Index("ix_data_change_history_changed_by", "changed_by"),
        Index("ix_data_change_history_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
