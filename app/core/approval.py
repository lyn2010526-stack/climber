"""Human-in-the-loop approval system for tool execution."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """Request for human approval before executing a tool."""

    session_id: str
    tool_name: str
    arguments: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    id: str = None
    created_at: datetime = None
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
    """Manages approval requests for tool execution."""

    def __init__(self):
        self._requests: dict[str, ApprovalRequest] = {}
        self._pending: dict[str, asyncio.Event] = {}

    async def request(self, session_id: str, tool_name: str, arguments: dict[str, Any]) -> ApprovalRequest:
        req = ApprovalRequest(session_id=session_id, tool_name=tool_name, arguments=arguments)
        self._requests[req.id] = req
        self._pending[req.id] = asyncio.Event()
        return req

    def approve(self, request_id: str, resolved_by: str = "human") -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None or req.status != ApprovalStatus.PENDING:
            return None
        req.approve(resolved_by)
        if request_id in self._pending:
            self._pending[request_id].set()
        return req

    def reject(self, request_id: str, reason: str = "", resolved_by: str = "human") -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None or req.status != ApprovalStatus.PENDING:
            return None
        req.reject(reason, resolved_by)
        if request_id in self._pending:
            self._pending[request_id].set()
        return req

    async def wait_for_decision(self, request_id: str, timeout: float | None = None) -> ApprovalRequest | None:
        event = self._pending.get(request_id)
        if event is None:
            return self._requests.get(request_id)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            req = self._requests.get(request_id)
            if req and req.status == ApprovalStatus.PENDING:
                req.reject(reason="timeout")
            return req
        return self._requests.get(request_id)

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def get_pending(self, session_id: str | None = None) -> list[ApprovalRequest]:
        requests = [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]
        if session_id:
            requests = [r for r in requests if r.session_id == session_id]
        return requests

    def list_all(self, limit: int | None = None) -> list[ApprovalRequest]:
        """Return all tracked requests (pending + resolved), newest first."""
        items = list(self._requests.values())
        items.sort(key=lambda r: r.created_at, reverse=True)
        if limit and limit > 0:
            items = items[:limit]
        return items

    def cleanup_old(self, max_age_seconds: float = 3600) -> None:
        import time
        now = time.time()
        old_ids = []
        for req_id, req in self._requests.items():
            def to_ts(val):
                if val is None:
                    return None
                if hasattr(val, 'timestamp'):
                    return val.timestamp()
                if isinstance(val, (int, float)):
                    return float(val)
                return None
            created = to_ts(req.created_at) or now
            resolved = to_ts(req.resolved_at)
            age = resolved or created
            if (now - age) > max_age_seconds:
                old_ids.append(req_id)
        for req_id in old_ids:
            self._requests.pop(req_id, None)
            self._pending.pop(req_id, None)
            self._pending.pop(req_id, None)


def tool_requires_approval(tool_name: str, arguments: dict[str, Any] | None = None) -> bool:
    """Check if a tool requires human approval based on configuration."""
    arguments = arguments or {}
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
