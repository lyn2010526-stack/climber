"""Human-in-the-loop approval system for tool execution."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import structlog
from pydantic import BaseModel
from sqlalchemy import and_, delete, or_, select, update

logger = structlog.get_logger()


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """Request for human approval before executing a tool."""

    user_id: str = "default-user"
    session_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    id: str | None = None
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    reason: str | None = None

    def __init__(self, **data: Any):
        if data.get("id") is None:
            data["id"] = str(uuid.uuid4())
        if data.get("created_at") is None:
            data["created_at"] = datetime.now(UTC)
        super().__init__(**data)

    def approve(self, resolved_by: str = "human") -> None:
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = datetime.now(UTC)
        self.resolved_by = resolved_by

    def reject(self, reason: str = "", resolved_by: str = "human") -> None:
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = datetime.now(UTC)
        self.resolved_by = resolved_by
        self.reason = reason

    def expire(self) -> None:
        self.status = ApprovalStatus.EXPIRED
        self.resolved_at = datetime.now(UTC)


class ApprovalManager:
    """Manages durable approval requests and local wake-up events.

    The database is the source of truth, which lets an approval created by one
    worker be listed and resolved by another. In-process events remain as a
    low-latency optimization; waiters also poll the database so they do not
    depend on sharing an event loop or process.
    """

    def __init__(self, poll_interval: float = 0.1):
        self._requests: dict[str, ApprovalRequest] = {}
        self._pending: dict[str, asyncio.Event] = {}
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._poll_interval = max(poll_interval, 0.01)

    @staticmethod
    def _db_datetime(value: datetime) -> datetime:
        """Store timestamps as naive UTC for SQLite/PostgreSQL parity."""
        return value.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def _request_datetime(value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)

    @classmethod
    def _from_record(cls, record: Any) -> ApprovalRequest:
        return ApprovalRequest(
            id=record.id,
            user_id=record.user_id,
            session_id=record.session_id,
            tool_name=record.tool_name,
            arguments=dict(record.arguments or {}),
            status=ApprovalStatus(record.status),
            created_at=cls._request_datetime(record.created_at),
            resolved_at=cls._request_datetime(record.resolved_at),
            resolved_by=record.resolved_by,
            reason=record.reason,
        )

    def _cache(self, request: ApprovalRequest) -> ApprovalRequest:
        self._requests[request.id] = request
        event = self._pending.setdefault(request.id, asyncio.Event())
        if request.status != ApprovalStatus.PENDING:
            event.set()
        return request

    async def _get_record(self, request_id: str, user_id: str | None = None) -> Any | None:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        statement = select(ApprovalRecord).where(ApprovalRecord.id == request_id)
        if user_id is not None:
            statement = statement.where(ApprovalRecord.user_id == user_id)
        async with async_session() as db:
            result = await db.execute(statement)
            return result.scalar_one_or_none()

    async def request(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str = "default-user",
    ) -> ApprovalRequest:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        req = ApprovalRequest(
            user_id=user_id,
            session_id=session_id,
            tool_name=tool_name,
            arguments=dict(arguments),
        )
        record = ApprovalRecord(
            id=req.id,
            user_id=req.user_id,
            session_id=req.session_id,
            tool_name=req.tool_name,
            arguments=req.arguments,
            status=req.status.value,
            created_at=self._db_datetime(req.created_at),
        )
        async with async_session() as db:
            db.add(record)
            await db.commit()
        return self._cache(req)

    async def get_request_async(self, request_id: str, user_id: str | None = None) -> ApprovalRequest | None:
        record = await self._get_record(request_id, user_id=user_id)
        if record is None:
            self._requests.pop(request_id, None)
            return None
        return self._cache(self._from_record(record))

    async def get_pending_async(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ApprovalRequest]:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        statement = select(ApprovalRecord).where(ApprovalRecord.status == ApprovalStatus.PENDING.value)
        if user_id is not None:
            statement = statement.where(ApprovalRecord.user_id == user_id)
        if session_id:
            statement = statement.where(ApprovalRecord.session_id == session_id)
        statement = statement.order_by(ApprovalRecord.created_at.asc())
        async with async_session() as db:
            result = await db.execute(statement)
            records = result.scalars().all()
        requests = []
        for record in records:
            request = self._from_record(record)
            self._cache(request)
            requests.append(request)
        return requests

    async def _resolve_async(
        self,
        request_id: str,
        status: ApprovalStatus,
        reason: str = "",
        resolved_by: str = "human",
        user_id: str | None = None,
    ) -> ApprovalRequest | None:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        now = self._db_datetime(datetime.now(UTC))
        values = {
            "status": status.value,
            "resolved_at": now,
            "resolved_by": resolved_by,
            "reason": reason or None,
        }
        identity_conditions = [ApprovalRecord.id == request_id]
        if user_id is not None:
            identity_conditions.append(ApprovalRecord.user_id == user_id)
        conditions = [
            ApprovalRecord.id == request_id,
            ApprovalRecord.status == ApprovalStatus.PENDING.value,
        ]
        if user_id is not None:
            conditions.append(ApprovalRecord.user_id == user_id)
        async with async_session() as db:
            result = await db.execute(
                update(ApprovalRecord)
                .where(and_(*conditions))
                .values(**values)
            )
            if not result.rowcount:
                await db.rollback()
                record = await db.scalar(select(ApprovalRecord).where(and_(*identity_conditions)))
                if record is not None:
                    self._cache(self._from_record(record))
                return None
            await db.commit()
            record = await db.scalar(select(ApprovalRecord).where(ApprovalRecord.id == request_id))
        if record is None:
            return None
        return self._cache(self._from_record(record))

    async def approve_async(
        self,
        request_id: str,
        resolved_by: str = "human",
        user_id: str | None = None,
    ) -> ApprovalRequest | None:
        return await self._resolve_async(
            request_id,
            ApprovalStatus.APPROVED,
            resolved_by=resolved_by,
            user_id=user_id,
        )

    async def reject_async(
        self,
        request_id: str,
        reason: str = "",
        resolved_by: str = "human",
        user_id: str | None = None,
    ) -> ApprovalRequest | None:
        return await self._resolve_async(
            request_id,
            ApprovalStatus.REJECTED,
            reason=reason,
            resolved_by=resolved_by,
            user_id=user_id,
        )

    async def resolve_async(
        self,
        request_id: str,
        decision: str,
        resolved_by: str = "human",
        user_id: str | None = None,
    ) -> ApprovalRequest | None:
        """Resolve a request using the durable store and an explicit decision."""
        if decision == "allow":
            return await self.approve_async(request_id, resolved_by=resolved_by, user_id=user_id)
        if decision == "deny":
            return await self.reject_async(request_id, resolved_by=resolved_by, user_id=user_id)
        raise ValueError(f"Unsupported approval decision: {decision}")

    def _schedule_resolution(
        self,
        request_id: str,
        status: ApprovalStatus,
        reason: str,
        resolved_by: str,
    ) -> None:
        # Safe by design: prefer the running loop and keep a strong reference
        # via self._background_tasks (discarded on done) so the task is never
        # GC'd mid-flight. asyncio.run is only used when no loop is running,
        # and _resolve_async opens a fresh async_session() per call, so no
        # loop-bound global session/engine is reused across loops.
        coroutine = self._resolve_async(request_id, status, reason, resolved_by)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coroutine)
            except Exception as exc:  # pragma: no cover - compatibility fallback
                logger.warning("approval.persistence_failed", request_id=request_id, error=str(exc))
            return
        task = loop.create_task(coroutine)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    @staticmethod
    def _run_sync(coroutine: Any) -> Any:
        """Run a durable coroutine for legacy callers outside an event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        coroutine.close()
        raise RuntimeError("Use the async approval API while an event loop is running")

    def approve(self, request_id: str, resolved_by: str = "human") -> ApprovalRequest | None:
        return self._run_sync(self.approve_async(request_id, resolved_by=resolved_by))

    def reject(self, request_id: str, reason: str = "", resolved_by: str = "human") -> ApprovalRequest | None:
        return self._run_sync(self.reject_async(request_id, reason=reason, resolved_by=resolved_by))

    def resolve(
        self,
        request_id: str,
        decision: str,
        resolved_by: str = "human",
        user_id: str | None = None,
    ) -> ApprovalRequest | None:
        return self._run_sync(
            self.resolve_async(
                request_id,
                decision,
                resolved_by=resolved_by,
                user_id=user_id,
            )
        )

    async def wait_for_decision(
        self,
        request_id: str,
        timeout: float | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ApprovalRequest | None:
        request = await self.get_request_async(request_id)
        if request is None or request.status != ApprovalStatus.PENDING:
            return request

        event = self._pending.setdefault(request_id, asyncio.Event())
        loop = asyncio.get_running_loop()
        deadline = None if timeout is None else loop.time() + max(timeout, 0)
        while True:
            if cancelled is not None and cancelled():
                cancelled_request = await self.reject_async(
                    request_id,
                    reason="session cancelled",
                    resolved_by="system",
                )
                return cancelled_request or await self.get_request_async(request_id)
            remaining = self._poll_interval
            if deadline is not None:
                remaining = min(remaining, max(0, deadline - loop.time()))
            try:
                await asyncio.wait_for(event.wait(), timeout=remaining)
            except TimeoutError:
                pass

            request = await self.get_request_async(request_id)
            if request is None or request.status != ApprovalStatus.PENDING:
                return request
            if deadline is not None and loop.time() >= deadline:
                timed_out = await self.reject_async(request_id, reason="timeout", resolved_by="system")
                return timed_out or await self.get_request_async(request_id)

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._run_sync(self.get_request_async(request_id))
        return self._requests.get(request_id)

    def get_pending(self, session_id: str | None = None) -> list[ApprovalRequest]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._run_sync(self.get_pending_async(session_id=session_id))
        requests = [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]
        if session_id:
            requests = [r for r in requests if r.session_id == session_id]
        return requests

    def list_all(self, limit: int | None = None) -> list[ApprovalRequest]:
        """Return all tracked requests (pending + resolved), newest first."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self._run_sync(self.list_all_async(limit=limit))
        items = list(self._requests.values())
        items.sort(key=lambda r: r.created_at, reverse=True)
        if limit and limit > 0:
            items = items[:limit]
        return items

    async def list_all_async(
        self,
        limit: int | None = None,
        user_id: str | None = None,
    ) -> list[ApprovalRequest]:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        statement = select(ApprovalRecord).order_by(ApprovalRecord.created_at.desc())
        if user_id is not None:
            statement = statement.where(ApprovalRecord.user_id == user_id)
        if limit is not None and limit > 0:
            statement = statement.limit(limit)
        async with async_session() as db:
            result = await db.execute(statement)
            records = result.scalars().all()
        requests = []
        for record in records:
            request = self._from_record(record)
            self._cache(request)
            requests.append(request)
        return requests

    async def count_async(self, user_id: str | None = None) -> int:
        from sqlalchemy import func

        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        statement = select(func.count()).select_from(ApprovalRecord)
        if user_id is not None:
            statement = statement.where(ApprovalRecord.user_id == user_id)
        async with async_session() as db:
            return int(await db.scalar(statement) or 0)

    async def cleanup_old_async(self, max_age_seconds: float = 3600) -> None:
        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        cutoff = self._db_datetime(datetime.now(UTC) - timedelta(seconds=max_age_seconds))
        condition = and_(
            ApprovalRecord.status != ApprovalStatus.PENDING.value,
            or_(
                ApprovalRecord.resolved_at < cutoff,
                and_(ApprovalRecord.resolved_at.is_(None), ApprovalRecord.created_at < cutoff),
            ),
        )
        async with async_session() as db:
            result = await db.execute(select(ApprovalRecord.id).where(condition))
            deleted_ids = list(result.scalars())
            await db.execute(delete(ApprovalRecord).where(condition))
            await db.commit()
        for request_id in deleted_ids:
            self._requests.pop(request_id, None)
            self._pending.pop(request_id, None)

    def cleanup_old(self, max_age_seconds: float = 3600) -> None:
        self._run_sync(self.cleanup_old_async(max_age_seconds))


def tool_requires_approval(tool_name: str, arguments: dict[str, Any] | None = None) -> bool:
    """Check if a tool requires human approval based on configuration."""
    arguments = arguments or {}
    # Inline LLM risk self-assessment: HIGH forces approval for any tool.
    from app.core.permission_controller import extract_security_risk

    if extract_security_risk(arguments) == "HIGH":
        return True
    approval_required_tools = {
        "run_command": lambda args: True,
        "execute_code": lambda args: True,
        "write_file": lambda args: True,
        "delete_file": lambda args: True,
        "network_request": lambda args: not args.get("url", "").startswith("https://"),
    }

    checker = approval_required_tools.get(tool_name)
    if checker:
        return checker(arguments)
    return False


approval_manager = ApprovalManager()
