"""Notification system data models.

This module defines all data models for the notification system including
notification templates, delivery records, user preferences, and device tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class NotificationType(StrEnum):
    """Types of notifications."""
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


class NotificationChannel(StrEnum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TELEGRAM = "telegram"


class NotificationStatus(StrEnum):
    """Status of notification delivery."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELED = "canceled"
    RETRYING = "retrying"


class NotificationPriority(StrEnum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationTemplate(Base):
    """Reusable notification template.

    Defines the structure and content of notifications that can be sent
    through various channels.

    Attributes:
        id: Unique template identifier.
        name: Template name.
        description: Template description.
        type: Notification type.
        channel: Delivery channel.
        subject: Email/SMS subject line.
        body_template: Template body with variable placeholders.
        html_template: HTML version for email.
        variables: List of template variables.
        locale: Language locale.
        version: Template version.
        is_active: Whether template is active.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "notification_templates"
    __table_args__ = (
        Index("ix_notification_templates_name", "name"),
        Index("ix_notification_templates_type", "type"),
        Index("ix_notification_templates_channel", "channel"),
        UniqueConstraint("name", "locale", "channel", name="uq_notification_template"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    html_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Notification(Base):
    """Individual notification instance.

    Represents a single notification sent to a user through a specific channel.

    Attributes:
        id: Unique notification identifier.
        user_id: Recipient user ID.
        template_id: Source template ID.
        type: Notification type.
        channel: Delivery channel.
        priority: Notification priority.
        status: Current delivery status.
        subject: Notification subject.
        body: Notification body content.
        data: Additional data for template rendering.
        sent_at: When notification was sent.
        delivered_at: When notification was delivered.
        read_at: When notification was read.
        error_message: Error message if delivery failed.
        retry_count: Number of delivery retries.
        max_retries: Maximum allowed retries.
        scheduled_at: Scheduled delivery time.
        metadata_json: Additional metadata.
        created_at: Creation timestamp.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_channel", "channel"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_scheduled_at", "scheduled_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    priority: Mapped[NotificationPriority] = mapped_column(SAEnum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(SAEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.read_at is not None

    @property
    def is_failed(self) -> bool:
        """Check if notification delivery failed."""
        return self.status == NotificationStatus.FAILED

    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return self.retry_count < self.max_retries and self.status == NotificationStatus.FAILED


class NotificationPreference(Base):
    """User notification preferences.

    Controls which notifications a user receives and through which channels.

    Attributes:
        id: Unique preference identifier.
        user_id: Associated user ID.
        type: Notification type preference applies to.
        channel: Channel preference applies to.
        enabled: Whether this notification type/channel is enabled.
        quiet_hours_start: Start of quiet hours.
        quiet_hours_end: End of quiet hours.
        quiet_hours_timezone: Timezone for quiet hours.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "notification_preferences"
    __table_args__ = (
        Index("ix_notification_preferences_user_id", "user_id"),
        UniqueConstraint("user_id", "type", "channel", name="uq_notification_preference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DeviceToken(Base):
    """Device token for push notifications.

    Stores device registration tokens for mobile push notifications.

    Attributes:
        id: Unique token identifier.
        user_id: Device owner user ID.
        token: Device registration token.
        platform: Device platform (ios, android, web).
        device_name: Human-readable device name.
        device_model: Device model identifier.
        os_version: Operating system version.
        app_version: Application version.
        is_active: Whether token is still valid.
        last_used_at: Last time token was used.
        created_at: Creation timestamp.
    """

    __tablename__ = "device_tokens"
    __table_args__ = (
        Index("ix_device_tokens_user_id", "user_id"),
        Index("ix_device_tokens_token", "token"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookEndpoint(Base):
    """Webhook endpoint configuration.

    Defines webhook endpoints that receive event notifications.

    Attributes:
        id: Unique endpoint identifier.
        user_id: Owner user ID.
        url: Webhook URL.
        secret: Signing secret for verification.
        events: List of events to subscribe to.
        is_active: Whether webhook is active.
        failure_count: Consecutive failure count.
        last_success_at: Last successful delivery.
        last_failure_at: Last failed delivery.
        created_at: Creation timestamp.
    """

    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
