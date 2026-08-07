"""Comprehensive notification schemas.

This module defines all Pydantic schemas for the notification system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NotificationTypeSchema(str, Enum):
    """Notification types."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"
    MARKETING = "marketing"
    SECURITY = "security"
    BILLING = "billing"
    SOCIAL = "social"
    REMINDER = "reminder"


class NotificationChannelSchema(str, Enum):
    """Notification channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationPrioritySchema(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationStatusSchema(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELED = "canceled"


# ── Template Schemas ──

class NotificationTemplateCreateSchema(BaseModel):
    """Schema for creating notification template."""
    name: str = Field(..., min_length=1, max_length=128)
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    subject: str | None = Field(None, max_length=255)
    body_template: str = Field(..., min_length=1)
    html_template: str | None = None
    variables: list[str] = Field(default_factory=list)
    locale: str = Field("en", min_length=2, max_length=16)
    description: str | None = None


class NotificationTemplateResponseSchema(BaseModel):
    """Schema for notification template response."""
    id: str
    name: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    subject: str | None
    body_template: str
    html_template: str | None
    variables: list[str]
    locale: str
    version: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Notification Schemas ──

class NotificationCreateSchema(BaseModel):
    """Schema for creating notification."""
    user_id: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    body: str = Field(..., min_length=1)
    subject: str | None = Field(None, max_length=255)
    priority: NotificationPrioritySchema = NotificationPrioritySchema.NORMAL
    data: dict[str, Any] | None = None
    template_id: str | None = None
    scheduled_at: datetime | None = None


class NotificationBulkCreateSchema(BaseModel):
    """Schema for bulk notification creation."""
    user_ids: list[str] = Field(..., min_length=1)
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    body: str
    subject: str | None = None


class NotificationResponseSchema(BaseModel):
    """Schema for notification response."""
    id: str
    user_id: str
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    priority: NotificationPrioritySchema
    status: NotificationStatusSchema
    subject: str | None
    body: str
    data: dict[str, Any] | None
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Preference Schemas ──

class NotificationPreferenceSchema(BaseModel):
    """Schema for notification preference."""
    type: NotificationTypeSchema
    channel: NotificationChannelSchema
    enabled: bool = True
    quiet_hours_start: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_timezone: str = "UTC"


class NotificationPreferenceUpdateSchema(BaseModel):
    """Schema for updating notification preference."""
    enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None


# ── Webhook Schemas ──

class WebhookCreateSchema(BaseModel):
    """Schema for creating webhook endpoint."""
    name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., max_length=512)
    events: list[str] = Field(..., min_length=1)


class WebhookResponseSchema(BaseModel):
    """Schema for webhook endpoint response."""
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    failure_count: int
    last_success_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Device Token Schemas ──

class DeviceTokenCreateSchema(BaseModel):
    """Schema for registering device token."""
    token: str = Field(..., min_length=1, max_length=512)
    platform: str = Field(..., pattern="^(ios|android|web)$")
    device_name: str | None = None
    device_model: str | None = None
    os_version: str | None = None
    app_version: str | None = None


class DeviceTokenResponseSchema(BaseModel):
    """Schema for device token response."""
    id: str
    token: str
    platform: str
    device_name: str | None
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Enums ──

