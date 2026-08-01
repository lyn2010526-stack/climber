"""Persistent task state machine with automatic database persistence."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_state_machine import TaskState, TaskStateMachine
from app.storage.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class PersistentTaskStateMachine(TaskStateMachine):
    """Task state machine that automatically persists state changes to database."""

    def __init__(self, task_id: str, task_repository: TaskRepository | None = None, **kwargs: Any):
        super().__init__(task_id=task_id, **kwargs)
        self.task_repository = task_repository or TaskRepository()

    async def transition(self, new_state: TaskState, trigger: str = "manual", db: AsyncSession | None = None) -> None:
        """Transition to new state and persist to database."""
        await super().transition(new_state, trigger)
        try:
            if db is not None:
                await self.task_repository.save_state(self.task_id, self, db)
            else:
                async with __import__("app.storage").storage.async_session() as session:
                    await self.task_repository.save_state(self.task_id, self, session)
        except Exception as e:
            logger.error("persistent_task_state_machine.persist_failed", task_id=self.task_id, error=str(e))
