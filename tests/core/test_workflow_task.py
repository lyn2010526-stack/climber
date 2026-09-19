"""Regression tests for the workflow task handler (missing Flow class).

The task_worker 'workflow' handler imports `Flow` from app.multi_agent.flow,
which previously had no Flow class, so the branch raised ImportError. Flow now
resolves a workflow definition by name and runs it through WorkflowEngine.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import AgentEvent, AgentEventType


class _FakeSession:
    pass


class _FakeEngine:
    def __init__(self, *args, **kwargs):
        self.sessions = []

    def create_session(self, **kwargs):
        self.sessions.append(kwargs)
        return _FakeSession()

    async def run(self, session, message):
        yield AgentEvent(type=AgentEventType.TEXT, data={"content": "hello workflow"})
        yield AgentEvent(type=AgentEventType.DONE, data={})


def _patch_di(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.di as di_module

    def _resolve(name):
        if name == "AgentEngine":
            return _FakeEngine()
        raise KeyError(name)

    monkeypatch.setattr(di_module, "resolve", _resolve)


def test_flow_module_exposes_flow_class() -> None:
    from app.multi_agent import flow as flow_module

    assert hasattr(flow_module, "Flow")
    assert callable(flow_module.Flow)


async def test_flow_executes_builtin_template_to_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.multi_agent.flow import Flow

    _patch_di(monkeypatch)
    result = await Flow(name="simple_qa").execute(params={"question": "hello"})
    assert result["status"] == "completed"
    assert result["outputs"]


async def test_flow_unknown_name_returns_structured_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.multi_agent.flow import Flow

    _patch_di(monkeypatch)
    result = await Flow(name="no_such_workflow").execute(params={})
    assert result["status"] == "failed"
    assert "no_such_workflow" in result["error"]


async def test_workflow_handler_returns_structured_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.task_worker import handle_workflow

    _patch_di(monkeypatch)

    ok = await handle_workflow(
        payload={"workflow": "simple_qa", "params": {"question": "hi"}},
        on_progress=None,
    )
    assert ok["status"] == "completed"

    missing = await handle_workflow(
        payload={"workflow": "ghost_flow", "params": {}},
        on_progress=None,
    )
    assert missing["status"] == "failed"
    assert "ghost_flow" in missing["error"]


def test_workflow_task_does_not_raise_importerror() -> None:
    from app.core.task_worker import handle_workflow
    from app.multi_agent.flow import Flow

    assert callable(handle_workflow)
    assert Flow is not None


async def test_workflow_task_failed_status_persists_on_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.task_worker import TaskManager, TaskStatus, handle_workflow
    from app.storage import async_session
    from app.storage.models_platform import AutoLoopTask

    _patch_di(monkeypatch)
    manager = TaskManager(max_workers=1)
    manager.register("workflow", handle_workflow)
    task_id = await manager.submit("workflow", {"workflow": "ghost_flow", "params": {}})

    async def _record_status() -> str:
        for _ in range(200):
            async with async_session() as session:
                record = await session.get(AutoLoopTask, task_id)
            if record and record.status in {"completed", "failed", "cancelled"}:
                return record.status
            await asyncio.sleep(0.05)
        raise AssertionError("task did not finish")

    status = await asyncio.wait_for(_record_status(), timeout=10)
    assert status == TaskStatus.FAILED.value
