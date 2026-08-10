"""Tests for the unified executor dispatcher and its adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.core.executor import (
    CrewExecutorAdapter,
    SkillComposerExecutorAdapter,
    UnifiedExecutor,
    WorkflowExecutorAdapter,
)
from app.core.interfaces import ExecutionContext, ExecutionResult, ExecutionStatus


@dataclass
class _Stub:
    """Minimal fake engine with success flag and optional error."""

    success: bool = True
    data: Any = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {"ok": True}

    async def execute(self, *args: Any, **kwargs: Any) -> _Stub:
        return self


def _ctx(**kw: Any) -> ExecutionContext:
    defaults = {"session_id": "s1", "user_id": "u1", "variables": {}, "metadata": {}}
    defaults.update(kw)
    return ExecutionContext(**defaults)


class _RaisingEngine:
    async def execute(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_unified_executor_unknown_type_fails():
    executor = UnifiedExecutor()
    result = await executor.execute(_ctx(), executor_type="nope")
    assert result.status is ExecutionStatus.FAILED
    assert "Unknown executor type" in result.error


@pytest.mark.asyncio
async def test_unified_executor_dispatch_to_adapter():
    adapter = WorkflowExecutorAdapter(_Stub())
    executor = UnifiedExecutor()
    executor.register_adapter("workflow", adapter)
    result = await executor.execute(_ctx(), executor_type="workflow", workflow={"id": "wf1"})
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output == {"ok": True}


@pytest.mark.asyncio
async def test_workflow_adapter_missing_workflow_fails():
    adapter = WorkflowExecutorAdapter(_Stub())
    result = await adapter.execute(_ctx())
    assert result.status is ExecutionStatus.FAILED
    assert "workflow is required" in result.error


@pytest.mark.asyncio
async def test_workflow_adapter_success():
    adapter = WorkflowExecutorAdapter(_Stub())
    result = await adapter.execute(_ctx(), workflow={"id": "wf1"})
    assert result.status is ExecutionStatus.COMPLETED
    assert result.output == {"ok": True}


@pytest.mark.asyncio
async def test_workflow_adapter_failed_result():
    adapter = WorkflowExecutorAdapter(_Stub(success=False, error="bad output"))
    result = await adapter.execute(_ctx(), workflow={"id": "wf1"})
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "bad output"


@pytest.mark.asyncio
async def test_workflow_adapter_exception_is_captured():
    adapter = WorkflowExecutorAdapter(_RaisingEngine())
    result = await adapter.execute(_ctx(), workflow={"id": "wf1"})
    assert result.status is ExecutionStatus.FAILED
    assert "boom" in result.error


@pytest.mark.asyncio
async def test_skill_composer_adapter_missing_composition_fails():
    adapter = SkillComposerExecutorAdapter(_Stub())
    result = await adapter.execute(_ctx())
    assert result.status is ExecutionStatus.FAILED
    assert "composition is required" in result.error


@pytest.mark.asyncio
async def test_skill_composer_adapter_success():
    adapter = SkillComposerExecutorAdapter(_Stub())
    result = await adapter.execute(_ctx(), composition={"nodes": []})
    assert result.status is ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_crew_adapter_success_and_failure():
    ok_adapter = CrewExecutorAdapter(_Stub())
    result = await ok_adapter.execute(_ctx())
    assert result.status is ExecutionStatus.COMPLETED

    bad_adapter = CrewExecutorAdapter(_Stub(success=False, error="crew failed"))
    result = await bad_adapter.execute(_ctx())
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "crew failed"


@pytest.mark.asyncio
async def test_execute_stream_yields_adapter_result_when_no_stream():
    adapter = WorkflowExecutorAdapter(_Stub())
    executor = UnifiedExecutor()
    executor.register_adapter("workflow", adapter)
    chunks = [chunk async for chunk in executor.execute_stream(_ctx(), executor_type="workflow", workflow={"id": "wf1"})]
    assert len(chunks) == 1
    assert chunks[0].status is ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_stream_unknown_type_raises():
    executor = UnifiedExecutor()
    with pytest.raises(ValueError):
        async for _ in executor.execute_stream(_ctx(), executor_type="missing"):
            pass


def test_execution_result_defaults():
    result = ExecutionResult(status=ExecutionStatus.COMPLETED)
    assert result.output is None
    assert result.error is None
    assert result.logs == []
