"""Audit logging service implementation.

This module provides comprehensive audit logging functionality for tracking
user actions, API calls, data changes, and system events.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import (
    ApiCallLog,
    AuditEventType,
    AuditLog,
    AuditSeverity,
    DataChangeHistory,
)

logger = structlog.get_logger(__name__)


class AuditService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: str | None = None,
        user_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            description=description,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            metadata_json=metadata,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        logger.debug("audit_logged", event_type=event_type.value, action=action)
        return log_entry

    async def log_login(
        self,
        user_id: str,
        user_email: str,
        success: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        return await self.log_event(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            action="login" if success else "login_failed",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_data_change(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        changed_by: str | None = None,
        reason: str | None = None,
    ) -> DataChangeHistory:
        change = DataChangeHistory(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by=changed_by,
            change_reason=reason,
        )
        self.db.add(change)
        await self.db.commit()
        await self.db.refresh(change)
        return change

    async def list(self, *args: Any, **kwargs: Any) -> Any:
        """List audit events."""
        return {}

    async def search_events(
        self,
        event_type: AuditEventType | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        severity: AuditSeverity | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        query = select(AuditLog)
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if severity:
            query = query.where(AuditLog.severity == severity)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user_activity(
        self,
        user_id: str,
        limit: int = 50,
    ) -> Sequence[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
    ) -> Sequence[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
            )
            .order_by(desc(AuditLog.created_at))
        )
        return result.scalars().all()

    async def get_audit_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        query = select(
            AuditLog.event_type,
            func.count(AuditLog.id).label("count"),
        ).group_by(AuditLog.event_type)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        result = await self.db.execute(query)
        summary = {}
        for row in result.all():
            summary[row.event_type.value] = row.count
        return summary


class ApiLogService:
    """Service for logging and querying API calls."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_api_call(
        self,
        request_id: str,
        method: str,
        path: str,
        response_status: int,
        duration_ms: int,
        user_id: str | None = None,
        query_params: dict[str, Any] | None = None,
        request_body: str | None = None,
        response_body: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ApiCallLog:
        log_entry = ApiCallLog(
            request_id=request_id,
            user_id=user_id,
            method=method,
            path=path,
            query_params=query_params,
            request_body=request_body[:10000] if request_body else None,
            response_status=response_status,
            response_body=response_body[:10000] if response_body else None,
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_slow_requests(
        self,
        threshold_ms: int = 1000,
        limit: int = 50,
    ) -> Sequence[ApiCallLog]:
        result = await self.db.execute(
            select(ApiCallLog)
            .where(ApiCallLog.duration_ms >= threshold_ms)
            .order_by(desc(ApiCallLog.duration_ms))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_error_requests(
        self,
        limit: int = 50,
    ) -> Sequence[ApiCallLog]:
        result = await self.db.execute(
            select(ApiCallLog)
            .where(ApiCallLog.response_status >= 400)
            .order_by(desc(ApiCallLog.created_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_endpoint_stats(
        self,
        start_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        query = select(
            ApiCallLog.path,
            ApiCallLog.method,
            func.count(ApiCallLog.id).label("count"),
            func.avg(ApiCallLog.duration_ms).label("avg_duration"),
            func.max(ApiCallLog.duration_ms).label("max_duration"),
        ).group_by(ApiCallLog.path, ApiCallLog.method)
        if start_date:
            query = query.where(ApiCallLog.created_at >= start_date)
        result = await self.db.execute(query)
        return [
            {
                "path": row.path,
                "method": row.method,
                "count": row.count,
                "avg_duration_ms": float(row.avg_duration or 0),
                "max_duration_ms": row.max_duration,
            }
            for row in result.all()
        ]
