"""Tests for human-in-the-loop approval system."""

from __future__ import annotations

import asyncio

import pytest

from app.core.approval import (
    ApprovalManager,
    ApprovalRequest,
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
        mgr.approve(approval.id)

    asyncio.create_task(approve_later())

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
        mgr.reject(approval.id)

    asyncio.create_task(reject_later())

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
        approval = await mgr.request("s1", "run_command", {"command": "a"})
        mgr.approve(approval.id)

        # Manually set resolved_at to old time
        import time
        approval.resolved_at = time.time() - 1000

        mgr.cleanup_old(max_age_seconds=600)
        assert approval.id not in mgr._pending

    asyncio.run(run())
