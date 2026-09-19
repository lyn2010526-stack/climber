"""Callback invocation and human-in-the-loop review for group collaboration."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.collaboration.constants import CALLBACK_REGISTRY
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask

logger = structlog.get_logger(__name__)


async def invoke_step_callback(task: Any, role: str, agent_id: str, output: str) -> None:
    """Invoke step callback if configured.

    Args:
        task: The task entity with step_callback configuration.
        role: The agent role (worker/reviewer).
        agent_id: The agent ID.
        output: The step output.
    """
    if not task.step_callback:
        return
    fn = CALLBACK_REGISTRY.get(task.step_callback)
    if not fn:
        logger.warning("step_callback_not_found", callback=task.step_callback)
        return
    try:
        result = fn(task_id=task.id, role=role, agent_id=agent_id, output=output)
        if asyncio.iscoroutine(result):
            await result
        await group_ws_hub.broadcast(task.group_id, {
            "type": "step_callback",
            "data": {"callback": task.step_callback, "role": role, "agent_id": agent_id},
        })
    except Exception as e:
        logger.error("step_callback_failed", task_id=task.id, error=str(e))


async def invoke_task_callback(task: Any, final_output: str) -> None:
    """Invoke task callback if configured.

    Args:
        task: The task entity with task_callback configuration.
        final_output: The final task output.
    """
    if not task.task_callback:
        return
    fn = CALLBACK_REGISTRY.get(task.task_callback)
    if not fn:
        logger.warning("task_callback_not_found", callback=task.task_callback)
        return
    try:
        result = fn(task_id=task.id, final_output=final_output)
        if asyncio.iscoroutine(result):
            await result
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_callback",
            "data": {"callback": task.task_callback, "task_id": task.id},
        })
    except Exception as e:
        logger.error("task_callback_failed", task_id=task.id, error=str(e))


async def wait_for_human_review(task: Any, output: str) -> bool:
    """Wait for human review if required.

    Args:
        task: The task entity with human_review_required configuration.
        output: The output awaiting review.

    Returns:
        True if approved, False if rejected or timed out.
    """
    if not task.human_review_required:
        return True

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "awaiting_human_review"
            await db.commit()

    await group_ws_hub.broadcast(task.group_id, {
        "type": "human_review_needed",
        "data": {"task_id": task.id, "output": output},
    })

    max_wait = task.human_review_timeout if hasattr(task, "human_review_timeout") and task.human_review_timeout else 3600
    waited = 0
    while waited < max_wait:
        await asyncio.sleep(5)
        waited += 5
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if not t:
                return False
            if t.human_review_status == "approved":
                return True
            if t.human_review_status == "rejected":
                return False
            if t.status in ("stopped", "failed"):
                return False

    logger.warning("human_review_timeout", task_id=task.id, waited_seconds=waited)
    return False
