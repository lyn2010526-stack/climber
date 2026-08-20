"""Unified executor interface and adapters for all orchestration engines.

This module provides the IExecutor interface and adapters that wrap:
- WorkflowEngine (DAG-based workflow execution)
- SkillComposer (skill chain orchestration)
- Crew (multi-agent collaboration)

All three implement the same IExecutor interface, enabling polymorphic use.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog

from app.core.interfaces import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStatus,
    IExecutor,
)

logger = structlog.get_logger()


# ── Workflow Engine Adapter ──

class WorkflowExecutorAdapter:
    def __init__(self, workflow_engine: Any) -> None:
        self._engine = workflow_engine

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ExecutionResult:
        workflow = kwargs.get("workflow")
        if workflow is None:
            return ExecutionResult(status=ExecutionStatus.FAILED, error="workflow is required")
        try:
            result = await self._engine.execute(
                workflow,
                user_inputs=context.variables,
                user_id=context.user_id,
            )
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED,
                output=result.data,
                error=result.error if hasattr(result, "error") else None,
            )
        except Exception as exc:
            logger.error("workflow_execution_failed", error=str(exc))
            return ExecutionResult(status=ExecutionStatus.FAILED, error=str(exc))


# ── Skill Composer Adapter ──

class SkillComposerExecutorAdapter:
    def __init__(self, composer: Any) -> None:
        self._composer = composer

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ExecutionResult:
        composition = kwargs.get("composition")
        if composition is None:
            return ExecutionResult(status=ExecutionStatus.FAILED, error="composition is required")
        try:
            result = await self._composer.execute(composition, context=context.variables)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED,
                output=result.data,
                error=result.error if hasattr(result, "error") else None,
            )
        except Exception as exc:
            logger.error("skill_composition_failed", error=str(exc))
            return ExecutionResult(status=ExecutionStatus.FAILED, error=str(exc))


# ── Crew Adapter ──

class CrewExecutorAdapter:
    def __init__(self, crew: Any) -> None:
        self._crew = crew

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ExecutionResult:
        try:
            output = await self._crew.execute(user_id=context.user_id)
            return ExecutionResult(
                status=ExecutionStatus.COMPLETED if output.success else ExecutionStatus.FAILED,
                output=output.data,
                error=output.error if hasattr(output, "error") else None,
            )
        except Exception as exc:
            logger.error("crew_execution_failed", error=str(exc))
            return ExecutionResult(status=ExecutionStatus.FAILED, error=str(exc))


# ── Unified Executor Dispatcher ──

class UnifiedExecutor(IExecutor):
    def __init__(self) -> None:
        self._adapters: dict[str, IExecutor] = {}

    def register_adapter(self, name: str, adapter: IExecutor) -> None:
        self._adapters[name] = adapter

    async def execute(self, context: ExecutionContext, **kwargs: Any) -> ExecutionResult:
        executor_type = kwargs.get("executor_type", "workflow")
        adapter = self._adapters.get(executor_type)
        if adapter is None:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=f"Unknown executor type: {executor_type}. Available: {list(self._adapters.keys())}",
            )
        return await adapter.execute(context, **kwargs)

    async def execute_stream(self, context: ExecutionContext, **kwargs: Any) -> AsyncIterator[Any]:
        executor_type = kwargs.get("executor_type", "workflow")
        adapter = self._adapters.get(executor_type)
        if adapter is None:
            raise ValueError(f"Unknown executor type: {executor_type}")
        if hasattr(adapter, "execute_stream"):
            async for chunk in adapter.execute_stream(context, **kwargs):
                yield chunk
        else:
            result = await adapter.execute(context, **kwargs)
            yield result
