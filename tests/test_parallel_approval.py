"""Tests for human-in-the-loop approval integration in parallel execution."""

from __future__ import annotations

import asyncio

import pytest

import app.core.approval as approval_module
from app.core.approval import ApprovalManager
from app.core.parallel import ParallelToolExecutor


class FakeRegistry:
    """Minimal registry stub: records calls, returns a fixed result."""

    def __init__(self, result: str = "ok"):
        self.calls: list[tuple[str, dict]] = []
        self._result = result

    async def execute(self, name: str, arguments: dict) -> str:
        self.calls.append((name, arguments))
        return self._result


class FakeSession:
    session_id = "session-test"


class FakeSessionAutoConfig(FakeSession):
    permission_config = None

    def __init__(self, config):
        self.permission_config = config


def _fresh_manager(monkeypatch: pytest.MonkeyPatch) -> ApprovalManager:
    manager = ApprovalManager()
    monkeypatch.setattr(approval_module, "approval_manager", manager)
    return manager


def _make_executor(registry: FakeRegistry, session: object | None) -> ParallelToolExecutor:
    return ParallelToolExecutor(registry, timeout_per_tool=5.0, session=session)


@pytest.mark.asyncio
async def test_approval_required_timeout_returns_permission_denied(monkeypatch):
    """Approval-required tool with no decision times out into a permission denial."""
    manager = _fresh_manager(monkeypatch)
    orig_wait = manager.wait_for_decision

    async def fast_wait(request_id: str, timeout: float | None = None):
        return await orig_wait(request_id, timeout=0.05)

    monkeypatch.setattr(manager, "wait_for_decision", fast_wait)

    registry = FakeRegistry()
    executor = _make_executor(registry, session=FakeSession())

    result = await executor._execute_one("run_command", {"command": "ls"}, tool_call_id="call-1")

    assert result.success is False
    assert "permission denied" in result.error
    assert registry.calls == []
    assert manager.get_pending() == []


@pytest.mark.asyncio
async def test_pre_allowed_by_permission_config_skips_approval(monkeypatch):
    """Sensitive tools pre-allowed by permission config skip the approval flow."""
    from app.core.permission_rules import get_auto_mode_config

    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="file written")
    session = FakeSessionAutoConfig(get_auto_mode_config())
    executor = _make_executor(registry, session=session)

    result = await executor._execute_one(
        "write_file",
        {"path": "/workspace/data/out.txt", "content": "hello"},
        tool_call_id="call-5",
    )

    assert result.success is True
    assert result.result == "file written"
    assert ("write_file", {"path": "/workspace/data/out.txt", "content": "hello"}) in registry.calls
    assert manager.get_pending() == []


@pytest.mark.asyncio
async def test_reject_returns_permission_denied(monkeypatch):
    """Rejecting the pending request blocks the tool from executing."""
    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="command output")
    executor = _make_executor(registry, session=FakeSession())

    async def reject_later():
        for _ in range(100):
            pending = manager.get_pending()
            if pending:
                manager.reject(pending[0].id, reason="not allowed")
                return
            await asyncio.sleep(0.01)
        raise AssertionError("no pending approval request")

    result, _ = await asyncio.gather(
        executor._execute_one("run_command", {"command": "rm -rf /"}, tool_call_id="call-4"),
        reject_later(),
    )

    assert result.success is False
    assert "permission denied" in result.error
    assert registry.calls == []
    assert manager.get_pending() == []
