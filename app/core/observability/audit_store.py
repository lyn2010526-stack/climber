"""Durable audit log for key agent operations.

Writes through the ORM to the ``audit_logs`` table so the compliance trail
survives process restarts. Every call is fail-open: an observability/storage
outage never changes the operation it is auditing nor raises into the caller.
"""

from __future__ import annotations

from sqlalchemy import func, select

LOGIN_ACTION = "auth:login"
PERMISSION_ACTION = "permission:decision"


def _default_factory():
    from app.storage import async_session

    return async_session


class DurableAuditStore:
    """Persistent, append-only audit writer for login, permission, file and agent events."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    def _sf(self):
        return self.session_factory or _default_factory()

    async def log(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        action: str,
        severity: str = "info",
        details: dict[str, object] | None = None,
        result: str = "",
    ) -> bool:
        try:
            from app.storage.models_memory import AuditLog

            async with self._sf()() as db:
                db.add(
                    AuditLog(
                        session_id=str(session_id) if session_id is not None else None,
                        user_id=str(user_id) if user_id is not None else None,
                        action=str(action)[:50],
                        severity=str(severity)[:20],
                        details=dict(details or {}),
                        result=str(result or "")[:2000],
                    )
                )
                await db.commit()
            return True
        except Exception:
            return False

    async def log_login(self, user_id=None, username=None, success=True, reason="") -> bool:
        return await self.log(
            user_id=user_id,
            action=LOGIN_ACTION,
            severity="warning" if not success else "info",
            details={"username": username, "success": bool(success), "reason": reason},
            result="granted" if success else "denied",
        )

    async def log_permission_decision(
        self,
        session_id=None,
        user_id=None,
        tool_name=None,
        allowed=None,
        reason="",
    ) -> bool:
        return await self.log(
            session_id=session_id,
            user_id=user_id,
            action=PERMISSION_ACTION,
            severity="warning" if not allowed else "info",
            details={"tool": tool_name, "allowed": bool(allowed), "reason": str(reason)[:500]},
            result="allowed" if allowed else "denied",
        )

    async def log_file_change(
        self, session_id=None, user_id=None, operation=None, path=None, details=None
    ) -> bool:
        return await self.log(
            session_id=session_id,
            user_id=user_id,
            action=f"file:{operation}",
            severity="critical" if operation in {"delete", "modify", "write"} else "info",
            details={"path": path, **(details or {})},
            result=operation or "",
        )

    async def log_agent_action(
        self, session_id=None, user_id=None, action=None, details=None
    ) -> bool:
        return await self.log(
            session_id=session_id,
            user_id=user_id,
            action=f"agent:{action}",
            details=details or {},
            result=action or "",
        )

    async def list_events(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
        action: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        try:
            from app.storage.models_memory import AuditLog

            query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            if user_id:
                query = query.where(AuditLog.user_id == str(user_id))
            if session_id:
                query = query.where(AuditLog.session_id == str(session_id))
            if action:
                query = query.where(AuditLog.action == str(action))
            if severity:
                query = query.where(AuditLog.severity == str(severity))
            query = query.limit(limit).offset(offset)
            async with self._sf()() as db:
                rows = (await db.execute(query)).scalars().all()
            return [
                {
                    "id": row.id,
                    "session_id": row.session_id,
                    "user_id": row.user_id,
                    "action": row.action,
                    "severity": row.severity,
                    "details": row.details,
                    "result": row.result,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
        except Exception:
            return []

    async def count_events(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
        action: str | None = None,
        severity: str | None = None,
    ) -> int:
        try:
            from app.storage.models_memory import AuditLog

            query = select(func.count()).select_from(AuditLog)
            if user_id:
                query = query.where(AuditLog.user_id == str(user_id))
            if session_id:
                query = query.where(AuditLog.session_id == str(session_id))
            if action:
                query = query.where(AuditLog.action == str(action))
            if severity:
                query = query.where(AuditLog.severity == str(severity))
            async with self._sf()() as db:
                return int((await db.execute(query)).scalar_one())
        except Exception:
            return 0


audit_log = DurableAuditStore()
