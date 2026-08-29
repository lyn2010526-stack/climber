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
    _stop_requested = False


class FakeSessionAutoConfig(FakeSession):
    permission_config = None

    def __init__(self, config):
        self.permission_config = config


class FakeStatefulSession(FakeSessionAutoConfig):
    def __init__(self, config):
        from app.core.task_state_machine import TaskState, TaskStateMachine

        super().__init__(config)
        self.state_machine = TaskStateMachine("session-test", initial_state=TaskState.PROCESSING)


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

    async def fast_wait(request_id: str, timeout: float | None = None, cancelled=None):
        return await orig_wait(request_id, timeout=0.05, cancelled=cancelled)

    monkeypatch.setattr(manager, "wait_for_decision", fast_wait)

    registry = FakeRegistry()
    executor = _make_executor(registry, session=FakeSession())

    result = await executor._execute_one("run_command", {"command": "ls"}, tool_call_id="call-1")

    assert result.success is False
    assert "permission denied" in result.error
    assert registry.calls == []
    assert manager.get_pending() == []


@pytest.mark.asyncio
async def test_stop_request_rejects_pending_approval_without_waiting_for_timeout(monkeypatch):
    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry()
    session = FakeSession()
    session._stop_requested = False
    executor = _make_executor(registry, session=session)

    run_task = asyncio.create_task(
        executor._execute_one("run_command", {"command": "ls"}, tool_call_id="call-stop")
    )
    for _ in range(100):
        pending = manager.get_pending()
        if pending:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError("no pending approval request")

    session._stop_requested = True
    result = await asyncio.wait_for(run_task, timeout=1)
    stored = await manager.get_request_async(pending[0].id)

    assert result.success is False
    assert "permission denied" in result.error
    assert registry.calls == []
    assert stored is not None
    assert stored.status == "rejected"
    assert stored.reason == "session cancelled"


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
async def test_permission_config_deny_blocks_execution_without_validator(monkeypatch):
    from app.core.permission_rules import PermissionConfig, PermissionMode

    _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="executed")
    session = FakeSessionAutoConfig(PermissionConfig(mode=PermissionMode.PLAN))
    executor = _make_executor(registry, session=session)

    result = await executor._execute_one(
        "write_file",
        {"path": "/workspace/data/out.txt", "content": "hello"},
        tool_call_id="call-denied",
    )

    assert result.success is False
    assert "permission denied" in result.error
    assert registry.calls == []


@pytest.mark.asyncio
async def test_stop_after_approval_prevents_tool_start(monkeypatch):
    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="executed")
    session = FakeSession()
    session._stop_requested = False
    executor = _make_executor(registry, session=session)

    async def approve_then_stop(request_id: str, timeout=None, cancelled=None):
        decision = await manager.approve_async(request_id)
        session._stop_requested = True
        return decision

    monkeypatch.setattr(manager, "wait_for_decision", approve_then_stop)
    result = await executor._execute_one(
        "run_command",
        {"command": "ls"},
        tool_call_id="call-approved-then-stopped",
    )

    assert result.success is False
    assert result.error == "cancelled"
    assert registry.calls == []


@pytest.mark.asyncio
async def test_validator_approval_request_is_not_overridden_by_allowed_config(monkeypatch):
    """A legacy overlay ASK decision still pauses a pre-allowed tool."""
    from app.core.permission_rules import get_auto_mode_config

    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="file written")
    session = FakeSessionAutoConfig(get_auto_mode_config())
    executor = ParallelToolExecutor(
        registry,
        timeout_per_tool=5.0,
        validator=lambda _name, _arguments: (True, "Approval required by overlay"),
        session=session,
    )

    run_task = asyncio.create_task(executor._execute_one(
        "write_file",
        {"path": "/workspace/data/out.txt", "content": "hello"},
        tool_call_id="call-overlay",
    ))
    for _ in range(100):
        pending = manager.get_pending()
        if pending:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError("no pending approval request")

    assert run_task.done() is False
    await manager.approve_async(pending[0].id)
    result = await run_task

    assert result.success is True
    assert registry.calls == [("write_file", {"path": "/workspace/data/out.txt", "content": "hello"})]


@pytest.mark.asyncio
async def test_parallel_approvals_resume_after_all_requests_are_resolved(monkeypatch):
    from app.core.permission_rules import get_default_config
    from app.core.task_state_machine import TaskState

    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="done")
    session = FakeStatefulSession(get_default_config())
    executor = _make_executor(registry, session=session)

    run_task = asyncio.create_task(executor.execute_all([
        {"id": "call-1", "function": {"name": "write_file", "arguments": {"path": "a"}}},
        {"id": "call-2", "function": {"name": "write_file", "arguments": {"path": "b"}}},
    ]))
    for _ in range(100):
        pending = manager.get_pending()
        if len(pending) == 2:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError("two approval requests were not created")

    assert session.state_machine.state == TaskState.PAUSED
    await manager.approve_async(pending[0].id)
    await asyncio.sleep(0)
    assert session.state_machine.state == TaskState.PAUSED
    assert run_task.done() is False

    await manager.approve_async(pending[1].id)
    results = await run_task
    assert session.state_machine.state == TaskState.PROCESSING
    assert all(result.success for result in results)


@pytest.mark.asyncio
async def test_concurrent_approval_count_returns_to_zero_and_resumes(monkeypatch):
    """Concurrent approvals must not lose count: final count is zero and state resumes PROCESSING."""
    from app.core.permission_rules import get_default_config
    from app.core.task_state_machine import TaskState

    manager = _fresh_manager(monkeypatch)
    registry = FakeRegistry(result="done")
    session = FakeStatefulSession(get_default_config())
    executor = _make_executor(registry, session=session)

    n = 8
    run_task = asyncio.create_task(executor.execute_all([
        {"id": f"call-{i}", "function": {"name": "write_file", "arguments": {"path": f"p{i}"}}}
        for i in range(n)
    ]))
    for _ in range(200):
        pending = manager.get_pending()
        if len(pending) == n:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError(f"expected {n} approval requests, got {len(manager.get_pending())}")

    assert getattr(session, "_pending_approval_count", 0) == n
    assert session.state_machine.state == TaskState.PAUSED

    for req in pending:
        await manager.approve_async(req.id)
        await asyncio.sleep(0)

    results = await asyncio.wait_for(run_task, timeout=5)
    assert session._pending_approval_count == 0
    assert session.state_machine.state == TaskState.PROCESSING
    assert all(result.success for result in results)
    assert len(registry.calls) == n
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
                await manager.reject_async(pending[0].id, reason="not allowed")
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
