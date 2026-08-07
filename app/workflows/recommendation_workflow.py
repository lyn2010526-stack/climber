"""Workflow module: recommendation - Automation and workflow engine."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class RecommendationWorkflowStatus(StrEnum):
    """Workflow status enum."""
    DRAFT = 'draft'
    ACTIVE = 'active'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class RecommendationStepStatus(StrEnum):
    """Step status enum."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class RecommendationTriggerType(StrEnum):
    """Trigger type enum."""
    MANUAL = 'manual'
    SCHEDULED = 'scheduled'
    EVENT = 'event'
    WEBHOOK = 'webhook'
    API = 'api'


@dataclass
class RecommendationWorkflowStep:
    """A single step in a workflow."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ''
    description: str = ''
    action: str = ''
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: str = 'pending'
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


@dataclass
class RecommendationWorkflowDefinition:
    """Definition of a workflow."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ''
    description: str = ''
    version: str = '1.0.0'
    steps: list[RecommendationWorkflowStep] = field(default_factory=list)
    triggers: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    status: str = 'draft'
    created_by: str = ''
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecommendationWorkflowExecution:
    """Running instance of a workflow."""
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ''
    status: str = 'pending'
    current_step_index: int = 0
    variables: dict[str, Any] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    triggered_by: str = ''


class RecommendationWorkflowEngine:
    """Main workflow engine."""

    def __init__(self):
        self._workflows: dict[str, RecommendationWorkflowDefinition] = {}
        self._executions: dict[str, RecommendationWorkflowExecution] = {}
        self._handlers: dict[str, Callable] = {}
        self._running: set[str] = set()

    def register_handler(self, action: str, handler: Callable) -> None:
        """Register action handler."""
        self._handlers[action] = handler
        logger.info("Handler registered", action=action)

    def create_workflow(self, definition: RecommendationWorkflowDefinition) -> str:
        """Create new workflow definition."""
        self._workflows[definition.id] = definition
        logger.info("Workflow created", workflow_id=definition.id, name=definition.name)
        return definition.id

    def get_workflow(self, workflow_id: str) -> RecommendationWorkflowDefinition | None:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: str | None = None) -> list[RecommendationWorkflowDefinition]:
        """List all workflows."""
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def update_workflow(self, workflow_id: str, **kwargs: Any) -> bool:
        """Update workflow definition."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        for key, value in kwargs.items():
            if hasattr(workflow, key):
                setattr(workflow, key, value)
        workflow.updated_at = datetime.utcnow()
        return True

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow definition."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    async def execute_workflow(
        self, workflow_id: str, triggered_by: str = '', variables: dict[str, Any] | None = None
    ) -> RecommendationWorkflowExecution | None:
        """Execute a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error("Workflow not found", workflow_id=workflow_id)
            return None

        execution = RecommendationWorkflowExecution(
            workflow_id=workflow_id,
            status='running',
            variables=variables or {},
            triggered_by=triggered_by,
            started_at=datetime.utcnow(),
        )
        self._executions[execution.id] = execution
        self._running.add(execution.id)

        try:
            for i, step in enumerate(workflow.steps):
                execution.current_step_index = i
                step.status = 'running'
                step.started_at = datetime.utcnow()
                await self._execute_step(step, execution)
                step.status = 'completed'
                step.completed_at = datetime.utcnow()
            execution.status = 'completed'
            execution.completed_at = datetime.utcnow()
        except Exception as e:
            execution.status = 'failed'
            logger.error("Workflow failed", execution_id=execution.id, error=str(e))
        finally:
            self._running.discard(execution.id)

        return execution

    async def _execute_step(self, step: RecommendationWorkflowStep, execution: RecommendationWorkflowExecution) -> None:
        """Execute single workflow step."""
        handler = self._handlers.get(step.action)
        if not handler:
            raise ValueError(f"No handler for action: {step.action}")
        if asyncio.iscoroutinefunction(handler):
            await handler(step.parameters, execution.variables)
        else:
            handler(step.parameters, execution.variables)

    def pause_execution(self, execution_id: str) -> bool:
        """Pause running execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == 'running':
            execution.status = 'paused'
            return True
        return False

    def resume_execution(self, execution_id: str) -> bool:
        """Resume paused execution."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == 'paused':
            execution.status = 'running'
            return True
        return False

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel execution."""
        execution = self._executions.get(execution_id)
        if execution:
            execution.status = 'cancelled'
            execution.completed_at = datetime.utcnow()
            self._running.discard(execution_id)
            return True
        return False

    def get_execution(self, execution_id: str) -> RecommendationWorkflowExecution | None:
        """Get execution by ID."""
        return self._executions.get(execution_id)

    def list_executions(self, workflow_id: str | None = None, status: str | None = None) -> list[RecommendationWorkflowExecution]:
        """List executions."""
        executions = list(self._executions.values())
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if status:
            executions = [e for e in executions if e.status == status]
        return executions

    def get_stats(self) -> dict[str, Any]:
        """Get engine statistics."""
        total_workflows = len(self._workflows)
        total_executions = len(self._executions)
        running = len(self._running)
        completed = sum(1 for e in self._executions.values() if e.status == 'completed')
        failed = sum(1 for e in self._executions.values() if e.status == 'failed')
        return {
            'total_workflows': total_workflows,
            'total_executions': total_executions,
            'running': running,
            'completed': completed,
            'failed': failed,
        }
