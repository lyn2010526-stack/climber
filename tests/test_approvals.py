"""Tests for human-in-the-loop approval system."""

from __future__ import annotations

import asyncio

import pytest

from app.core.approval import (
    ApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
    tool_requires_approval,
)


def test_approval_request_creation():
    """Test creating an approval request."""
    req = ApprovalRequest(
        session_id="session-1",
        tool_name="run_command",
        arguments={"command": "ls"},
    )
    assert req.status == "pending"
    assert req.tool_name == "run_command"
    assert req.id is not None


def test_approval_approve():
    """Test approving a request."""
    req = ApprovalRequest(
        session_id="s1",
        tool_name="run_command",
        arguments={},
    )
    req.approve()
    assert req.status == "approved"
    assert req.resolved_at is not None


def test_approval_reject():
    """Test rejecting a request."""
    req = ApprovalRequest(
        session_id="s1",
        tool_name="run_command",
        arguments={},
    )
    req.reject()
    assert req.status == "rejected"


def test_tool_requires_approval():
    """Test approval requirement check."""
    assert tool_requires_approval("run_command") is True
    assert tool_requires_approval("write_file") is True
    assert tool_requires_approval("calculator") is False
    assert tool_requires_approval("web_search") is False


@pytest.mark.asyncio
async def test_approval_manager_request_and_approve():
    """Test full approval flow: request -> approve -> resolved."""
    mgr = ApprovalManager()

    # Create request
    approval = await mgr.request("session-1", "run_command", {"command": "ls"})
    assert approval.status == "pending"

    # Approve from another task
    async def approve_later():
        await asyncio.sleep(0.05)
        await mgr.approve_async(approval.id)

    asyncio.create_task(approve_later())  # noqa: RUF006 - test-specific pattern

    # Wait for decision
    result = await mgr.wait_for_decision(approval.id, timeout=5.0)
    assert result.status == "approved"


@pytest.mark.asyncio
async def test_approval_manager_reject():
    """Test rejection flow."""
    mgr = ApprovalManager()
    approval = await mgr.request("session-1", "run_command", {"command": "rm -rf /"})

    async def reject_later():
        await asyncio.sleep(0.05)
        await mgr.reject_async(approval.id)

    asyncio.create_task(reject_later())  # noqa: RUF006 - test-specific pattern

    result = await mgr.wait_for_decision(approval.id, timeout=5.0)
    assert result.status == "rejected"


@pytest.mark.asyncio
async def test_approval_manager_timeout():
    """Test approval timeout auto-rejects."""
    mgr = ApprovalManager()
    approval = await mgr.request("session-1", "run_command", {"command": "ls"})

    # Don't approve - let it timeout
    result = await mgr.wait_for_decision(approval.id, timeout=0.1)
    assert result.status == "rejected"


@pytest.mark.asyncio
async def test_approval_manager_persists_requests_across_instances():
    """A second manager instance can observe and resolve a request."""
    creator = ApprovalManager()
    resolver = ApprovalManager()

    approval = await creator.request("shared-session", "run_command", {"command": "ls"})

    pending = await resolver.get_pending_async(session_id="shared-session")
    assert [request.id for request in pending] == [approval.id]

    resolved = await resolver.approve_async(approval.id, resolved_by="worker-2")
    assert resolved is not None
    assert resolved.status == "approved"

    result = await creator.wait_for_decision(approval.id, timeout=1.0)
    assert result is not None
    assert result.status == "approved"
    assert result.resolved_by == "worker-2"


@pytest.mark.asyncio
async def test_approval_manager_resolution_is_atomic_across_instances():
    """Only one concurrent resolver can transition a pending request."""
    creator = ApprovalManager()
    first_resolver = ApprovalManager()
    second_resolver = ApprovalManager()
    approval = await creator.request("shared-session", "write_file", {"path": "/tmp/a"})

    first, second = await asyncio.gather(
        first_resolver.approve_async(approval.id, resolved_by="worker-1"),
        second_resolver.reject_async(approval.id, reason="denied", resolved_by="worker-2"),
    )

    assert sum(result is not None for result in (first, second)) == 1
    stored = await creator.get_request_async(approval.id)
    assert stored is not None
    assert stored.status in ("approved", "rejected")


@pytest.mark.asyncio
async def test_sync_resolution_is_rejected_inside_running_event_loop():
    """Sync compatibility methods must not report success before DB commit."""
    manager = ApprovalManager()
    approval = await manager.request("session-1", "write_file", {"path": "/tmp/a"})

    with pytest.raises(RuntimeError, match="async approval API"):
        manager.approve(approval.id)

    stored = await manager.get_request_async(approval.id)
    assert stored is not None
    assert stored.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_resolve_async_rejects_unknown_decision():
    manager = ApprovalManager()
    approval = await manager.request("session-1", "write_file", {"path": "/tmp/a"})

    with pytest.raises(ValueError, match="Unsupported approval decision"):
        await manager.resolve_async(approval.id, "typo")

    stored = await manager.get_request_async(approval.id)
    assert stored is not None
    assert stored.status == ApprovalStatus.PENDING


def test_sync_compatibility_reads_durable_requests_across_instances():
    """Legacy synchronous lookups can observe requests created elsewhere."""
    creator = ApprovalManager()
    approval = asyncio.run(creator.request("shared-session", "run_command", {"command": "ls"}))
    resolver = ApprovalManager()

    pending = resolver.get_pending(session_id="shared-session")
    stored = resolver.get_request(approval.id)

    assert [request.id for request in pending] == [approval.id]
    assert stored is not None
    assert stored.status == "pending"


def test_sync_compatibility_resolution_is_durable_across_instances():
    """Legacy synchronous resolution returns the durable state transition."""
    creator = ApprovalManager()
    approval = asyncio.run(creator.request("shared-session", "write_file", {"path": "/tmp/a"}))
    resolver = ApprovalManager()

    resolved = resolver.approve(approval.id, resolved_by="worker-2")
    stored = asyncio.run(creator.get_request_async(approval.id))

    assert resolved is not None
    assert resolved.status == "approved"
    assert stored is not None
    assert stored.status == "approved"
    assert stored.resolved_by == "worker-2"


def test_get_pending_approvals():
    """Test listing pending approvals."""
    mgr = ApprovalManager()

    async def run():
        await mgr.request("s1", "run_command", {"command": "a"})
        await mgr.request("s2", "write_file", {"path": "b"})

        pending = mgr.get_pending()
        assert len(pending) == 2

        pending_s1 = mgr.get_pending(session_id="s1")
        assert len(pending_s1) == 1

    asyncio.run(run())


def test_cleanup_old_approvals():
    """Test cleanup of old resolved approvals."""
    mgr = ApprovalManager()

    async def run():
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import update

        from app.storage import async_session
        from app.storage.database import ApprovalRecord

        approval = await mgr.request("s1", "run_command", {"command": "a"})
        await mgr.approve_async(approval.id)

        async with async_session() as db:
            await db.execute(
                update(ApprovalRecord)
                .where(ApprovalRecord.id == approval.id)
                .values(resolved_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1000))
            )
            await db.commit()

        await mgr.cleanup_old_async(max_age_seconds=600)
        assert approval.id not in mgr._pending
        assert await mgr.get_request_async(approval.id) is None

    asyncio.run(run())
