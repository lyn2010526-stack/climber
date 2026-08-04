"""Task state persistence repository."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models_groups import AgentGroupTask
from app.core.task_state_machine import TaskState, TaskStateMachine

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for task state persistence."""

    async def get_state_machine(self, task_id: str, db: AsyncSession) -> TaskStateMachine | None:
        """Load task state from database and return a TaskStateMachine."""
        query = select(AgentGroupTask).where(AgentGroupTask.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if task is None:
            return None
        
        status_map = {
            "pending": "pending",
            "processing": "processing",
            "running": "processing",
            "paused": "paused",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
            "stopped": "cancelled",
            "partial": "failed",
            "awaiting_human_review": "paused",
        }
        normalized = status_map.get(task.status, "pending")
        initial_state = TaskState(normalized)
        metadata = {
            "task_id": task.id,
            "group_id": task.group_id,
            "agent_id": task.agent_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }
        return TaskStateMachine(task_id=task_id, initial_state=initial_state, metadata=metadata)

    async def save_state(self, task_id: str, state_machine: TaskStateMachine, db: AsyncSession) -> None:
        """Persist task state machine to database."""
        try:
            db_status_map = {
                TaskState.PENDING: "pending",
                TaskState.PROCESSING: "running",
                TaskState.PAUSED: "paused",
                TaskState.COMPLETED: "completed",
                TaskState.FAILED: "failed",
                TaskState.CANCELLED: "stopped",
                TaskState.RETRYING: "running",
            }
            db_status = db_status_map.get(state_machine.state, state_machine.state.value)
            stmt = (
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .values(
                    status=db_status,
                )
            )
            await db.execute(stmt)
        except Exception as e:
            logger.error("task_repository.save_state_failed", task_id=task_id, error=str(e))
            raise

    async def save_context_data(self, task_id: str, context_data: dict[str, Any], db: AsyncSession) -> None:
        """Persist task context data (shared state between agents)."""
        try:
            stmt = (
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .values(
                    context_data=context_data,
                )
            )
            await db.execute(stmt)
        except Exception as e:
            logger.error("task_repository.save_context_failed", task_id=task_id, error=str(e))
            raise

    async def get_context_data(self, task_id: str, db: AsyncSession) -> dict[str, Any]:
        """Load task context data from database."""
        query = select(AgentGroupTask.context_data).where(AgentGroupTask.id == task_id)
        result = await db.execute(query)
        row = result.scalar_one_or_none()
        return row if row else {}
