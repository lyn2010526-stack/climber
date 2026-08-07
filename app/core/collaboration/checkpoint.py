"""Checkpoint management for group collaboration task resumption."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask, AgentGroupTaskCheckpoint

logger = structlog.get_logger(__name__)


async def save_checkpoint(
    task_id: str,
    group_id: str,
    current_round: int,
    max_rounds: int,
    current_artifact: str,
    all_issues: list[dict[str, Any]],
) -> None:
    """Save execution checkpoint for resume capability.

    Args:
        task_id: The task ID.
        group_id: The group ID.
        current_round: The current execution round.
        max_rounds: The maximum number of rounds.
        current_artifact: The current output artifact.
        all_issues: List of issues identified so far.
    """
    async with async_session() as db:
        task = await db.get(AgentGroupTask, task_id)
        checkpoint = AgentGroupTaskCheckpoint(
            group_id=group_id,
            task_id=task_id,
            status="running",
            current_round=current_round,
            max_rounds=max_rounds,
            current_artifact=current_artifact,
            all_issues=all_issues,
            task_description=task.description if task else "",
            output_schema=task.output_schema if task else {},
        )
        db.add(checkpoint)
        await db.commit()


async def load_latest_checkpoint(task_id: str) -> AgentGroupTaskCheckpoint | None:
    """Load the latest checkpoint for a task.

    Args:
        task_id: The task ID to load checkpoint for.

    Returns:
        The latest checkpoint or None if not found.
    """
    async with async_session() as db:
        result = (
            await db.execute(
                select(AgentGroupTaskCheckpoint)
                .where(AgentGroupTaskCheckpoint.task_id == task_id)
                .order_by(AgentGroupTaskCheckpoint.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return result


async def resume_from_checkpoint(task: Any, checkpoint: AgentGroupTaskCheckpoint) -> None:
    """Resume task execution from a checkpoint.

    Args:
        task: The task entity to resume.
        checkpoint: The checkpoint to resume from.
    """
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "running"
            t.final_output = checkpoint.current_artifact
            t.current_round = checkpoint.current_round
            await db.commit()

    await group_ws_hub.broadcast(task.group_id, {
        "type": "checkpoint_restored",
        "data": {"task_id": task.id, "checkpoint_id": checkpoint.id, "round": checkpoint.current_round},
    })
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_partial",
        "data": {"task_id": task.id, "final_output": checkpoint.current_artifact, "rounds": checkpoint.current_round},
    })
