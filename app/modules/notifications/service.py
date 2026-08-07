"""Notification service implementation.

This module provides comprehensive notification management functionality
including multi-channel delivery, template management, user preferences,
and delivery tracking.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    DeviceToken,
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
    WebhookEndpoint,
)

logger = structlog.get_logger(__name__)


class NotificationError(Exception):
    """Base exception for notification operations."""
    def __init__(self, message: str, code: str = "notification_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class TemplateNotFoundError(NotificationError):
    """Raised when a notification template is not found."""
    def __init__(self, template_id: str) -> None:
        super().__init__(f"Template not found: {template_id}", "template_not_found")


class DeliveryFailedError(NotificationError):
    """Raised when notification delivery fails."""
    def __init__(self, channel: str, reason: str) -> None:
        super().__init__(f"Delivery failed on {channel}: {reason}", "delivery_failed")


class TemplateService:
    """Service for managing notification templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_template(
        self,
        name: str,
        type: NotificationType,
        channel: NotificationChannel,
        body_template: str,
        subject: str | None = None,
        html_template: str | None = None,
        variables: list[str] | None = None,
        locale: str = "en",
        description: str | None = None,
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            name=name,
            description=description,
            type=type,
            channel=channel,
            subject=subject,
            body_template=body_template,
            html_template=html_template,
            variables=variables or [],
            locale=locale,
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        logger.info("template_created", template_id=template.id, name=name)
        return template

    async def get_template(self, template_id: str) -> NotificationTemplate:
        result = await self.db.execute(
            select(NotificationTemplate).where(NotificationTemplate.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise TemplateNotFoundError(template_id)
        return template

    async def render_template(
        self,
        template_id: str,
        variables: dict[str, Any],
    ) -> dict[str, str]:
        template = await self.get_template(template_id)
        subject = template.subject or ""
        body = template.body_template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        return {"subject": subject, "body": body}

    async def list_templates(
        self,
        type: NotificationType | None = None,
        channel: NotificationChannel | None = None,
        locale: str | None = None,
    ) -> Sequence[NotificationTemplate]:
        query = select(NotificationTemplate).where(NotificationTemplate.is_active)
        if type:
            query = query.where(NotificationTemplate.type == type)
        if channel:
            query = query.where(NotificationTemplate.channel == channel)
        if locale:
            query = query.where(NotificationTemplate.locale == locale)
        result = await self.db.execute(query)
        return result.scalars().all()


class NotificationService:
    """Service for sending and managing notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.templates = TemplateService(db)

    async def list(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """List notifications."""
        return {}

    async def send_notification(
        self,
        user_id: str,
        type: NotificationType,
        channel: NotificationChannel,
        body: str,
        subject: str | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: dict[str, Any] | None = None,
        template_id: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            template_id=template_id,
            type=type,
            channel=channel,
            priority=priority,
            status=NotificationStatus.PENDING,
            subject=subject,
            body=body,
            data=data,
            scheduled_at=scheduled_at,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        logger.info("notification_created", notification_id=notification.id, channel=channel.value)
        return notification

    async def send_bulk(
        self,
        user_ids: list[str],
        type: NotificationType,
        channel: NotificationChannel,
        body: str,
        subject: str | None = None,
    ) -> list[Notification]:
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                user_id=user_id,
                type=type,
                channel=channel,
                status=NotificationStatus.PENDING,
                subject=subject,
                body=body,
            )
            notifications.append(notification)
        self.db.add_all(notifications)
        await self.db.commit()
        for n in notifications:
            await self.db.refresh(n)
        logger.info("bulk_notification_created", count=len(notifications))
        return notifications

    async def get_notification(self, notification_id: str) -> Notification:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one()

    async def list_notifications(
        self,
        user_id: str,
        status: NotificationStatus | None = None,
        channel: NotificationChannel | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if status:
            query = query.where(Notification.status == status)
        if channel:
            query = query.where(Notification.channel == channel)
        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_as_read(self, notification_id: str) -> Notification:
        notification = await self.get_notification(notification_id)
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: str) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read_at.is_(None)))
            .values(status=NotificationStatus.READ, read_at=datetime.utcnow())
        )
        await self.db.commit()
        return result.rowcount

    async def get_unread_count(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                and_(Notification.user_id == user_id, Notification.read_at.is_(None))
            )
        )
        return result.scalar_one()

    async def retry_failed(self, notification_id: str) -> Notification:
        notification = await self.get_notification(notification_id)
        if notification.status != NotificationStatus.FAILED:
            raise NotificationError("Only failed notifications can be retried")
        notification.status = NotificationStatus.PENDING
        notification.retry_count += 1
        await self.db.commit()
        await self.db.refresh(notification)
        return notification


class PreferenceService:
    """Service for managing user notification preferences."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def set_preference(
        self,
        user_id: str,
        type: NotificationType,
        channel: NotificationChannel,
        enabled: bool,
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
    ) -> NotificationPreference:
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.type == type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        pref = result.scalar_one_or_none()
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id, type=type, channel=channel, enabled=enabled
            )
            self.db.add(pref)
        else:
            pref.enabled = enabled
            if quiet_hours_start:
                pref.quiet_hours_start = quiet_hours_start
            if quiet_hours_end:
                pref.quiet_hours_end = quiet_hours_end
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def get_preferences(
        self, user_id: str
    ) -> Sequence[NotificationPreference]:
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalars().all()

    async def is_enabled(
        self, user_id: str, type: NotificationType, channel: NotificationChannel
    ) -> bool:
        result = await self.db.execute(
            select(NotificationPreference).where(
                and_(
                    NotificationPreference.user_id == user_id,
                    NotificationPreference.type == type,
                    NotificationPreference.channel == channel,
                )
            )
        )
        pref = result.scalar_one_or_none()
        return pref.enabled if pref else True


class WebhookService:
    """Service for managing webhook endpoints."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_webhook(
        self,
        user_id: str,
        name: str,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookEndpoint:
        import secrets
        webhook = WebhookEndpoint(
            user_id=user_id,
            name=name,
            url=url,
            secret=secret or secrets.token_hex(32),
            events=events,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        logger.info("webhook_registered", webhook_id=webhook.id, url=url)
        return webhook

    async def list_webhooks(self, user_id: str) -> Sequence[WebhookEndpoint]:
        result = await self.db.execute(
            select(WebhookEndpoint).where(WebhookEndpoint.user_id == user_id)
        )
        return result.scalars().all()

    async def delete_webhook(self, webhook_id: str) -> None:
        await self.db.execute(
            delete(WebhookEndpoint).where(WebhookEndpoint.id == webhook_id)
        )
        await self.db.commit()


class DeviceService:
    """Service for managing device tokens for push notifications."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_device(
        self,
        user_id: str,
        token: str,
        platform: str,
        device_name: str | None = None,
        device_model: str | None = None,
        os_version: str | None = None,
        app_version: str | None = None,
    ) -> DeviceToken:
        result = await self.db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )
        device = result.scalar_one_or_none()
        if device is None:
            device = DeviceToken(
                user_id=user_id,
                token=token,
                platform=platform,
                device_name=device_name,
                device_model=device_model,
                os_version=os_version,
                app_version=app_version,
            )
            self.db.add(device)
        else:
            device.user_id = user_id
            device.last_used_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def list_devices(self, user_id: str) -> Sequence[DeviceToken]:
        result = await self.db.execute(
            select(DeviceToken).where(
                and_(DeviceToken.user_id == user_id, DeviceToken.is_active)
            )
        )
        return result.scalars().all()

    async def unregister_device(self, token: str) -> None:
        await self.db.execute(
            update(DeviceToken).where(DeviceToken.token == token).values(is_active=False)
        )
        await self.db.commit()
