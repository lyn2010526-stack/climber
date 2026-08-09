"""Hierarchical process implementation for group collaboration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.core.collaboration.agent_runner import run_agent_simple, run_agent_with_retry
from app.core.collaboration.callbacks import invoke_step_callback, invoke_task_callback
from app.core.collaboration.memory import store_memory
from app.core.collaboration.prompts import (
    build_manager_planning_prompt,
    build_manager_prompt,
    build_manager_validation_prompt,
    build_worker_prompt,
)
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupMember

logger = structlog.get_logger(__name__)


async def run_hierarchical_process(task: Any, group: Any) -> None:
    """Hierarchical execution: manager agent delegates and validates."""
    manager_member = await _find_manager(group)
    if not manager_member:
        logger.error("no_manager_found", group_id=group.id)
        return

    workers = [m for m in group.members if m.id != manager_member.id and m.role in ("worker", "participant")]
    if not workers:
        logger.error("no_workers_found", group_id=group.id)
        return

    await group_ws_hub.broadcast(task.group_id, {
        "type": "manager_start",
        "data": {"member_id": manager_member.id, "member_name": manager_member.agent_id},
    })

    manager_plan = await _plan_subtasks(task, manager_member)
    if not manager_plan:
        return

    await group_ws_hub.broadcast(task.group_id, {
        "type": "hierarchical_plan",
        "data": {"content": manager_plan, "tokens_used": 0},
    })

    subtask_outputs = await _delegate_subtasks(task, workers, manager_plan)
    manager_validation = await _validate_output(task, manager_member, manager_plan, subtask_outputs)

    lower_validation = manager_validation.lower()
    passed = any(k in lower_validation for k in ["通过", "pass", "approved", "acceptable", "valid"])
    final_output = manager_validation if passed else "\n\n".join(subtask_outputs.values())

    async with async_session() as db:
        t = await db.get(__import__("app.storage.models_groups", fromlist=["AgentGroupTask"]).AgentGroupTask, task.id)
        if t:
            t.status = "completed" if passed else "partial"
            t.final_output = final_output
            t.completed_at = datetime.now(UTC)
            await db.commit()

    await store_memory(task.group_id, task.id, manager_member.agent_id, final_output, "task_result")
    await invoke_task_callback(task, final_output)

    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_completed" if passed else "task_partial",
        "data": {"task_id": task.id, "final_output": final_output, "manager_validation": manager_validation},
    })


async def _find_manager(group: Any) -> AgentGroupMember | None:
    """Find the manager member in a group."""
    if group.manager_agent_id:
        async with async_session() as db:
            manager = (
                await db.execute(
                    select(AgentGroupMember).where(
                        AgentGroupMember.id == group.manager_agent_id,
                        AgentGroupMember.group_id == group.id,
                    )
                )
            ).scalar_one_or_none()
            if manager:
                return manager

    async with async_session() as db:
        candidates = (
            await db.execute(
                select(AgentGroupMember).where(
                    AgentGroupMember.group_id == group.id,
                    AgentGroupMember.role.in_(["manager", "coordinator", "worker"]),
                )
            )
        ).scalars().all()
        return candidates[0] if candidates else None


async def _plan_subtasks(task: Any, manager: Any) -> str:
    """Have the manager plan subtasks."""
    from app.core.collaboration.constants import TASK_TIMEOUT

    subtask_prompt = build_manager_planning_prompt(task.description, [m for m in task.group_members or [] if m.id != manager.id])
    try:
        async with __import__("asyncio").timeout(TASK_TIMEOUT):
            manager_plan, _ = await run_agent_simple(
                agent_id=manager.agent_id,
                provider=manager.model_provider or "openai",
                model_id=manager.model_id or "gpt-4o",
                api_key=resolve_api_key(manager.model_provider, manager.api_key_encrypted),
                base_url=resolve_base_url(manager.model_provider, None),
                system_prompt=build_manager_prompt(task.description),
                user_message=subtask_prompt,
                tools=manager.tools or [],
            )
        return manager_plan
    except Exception as e:
        logger.error("manager_failed", task_id=task.id, error=str(e))
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_failed",
            "data": {"task_id": task.id, "error": f"Manager planning failed: {e}"},
        })
        return ""


async def _delegate_subtasks(task: Any, workers: list[Any], manager_plan: str) -> dict[str, str]:
    """Delegate subtasks to workers and collect outputs."""
    subtask_outputs: dict[str, str] = {}
    for i, worker in enumerate(workers):
        subtask_desc = f"{task.description}\n\nContext from manager: {manager_plan}\n"
        if i > 0 and subtask_outputs:
            previous = list(subtask_outputs.values())[-1]
            subtask_desc += f"\nPrevious subtask output: {previous}\n"

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_delegate",
            "data": {"worker_id": worker.id, "worker_name": worker.agent_id, "subtask_index": i + 1},
        })

        worker_output, worker_tokens = await run_agent_with_retry(
            agent_id=worker.agent_id,
            provider=worker.model_provider or "openai",
            model_id=worker.model_id or "gpt-4o",
            api_key=resolve_api_key(worker.model_provider, worker.api_key_encrypted),
            system_prompt=build_worker_prompt(subtask_desc),
            user_message=subtask_desc,
            tools=worker.tools or [],
            group_id=task.group_id,
            role="worker",
        )
        subtask_outputs[worker.id] = worker_output

        await invoke_step_callback(task, "worker", worker.agent_id, worker_output)

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_delegate_done",
            "data": {"worker_id": worker.id, "worker_name": worker.agent_id, "subtask_index": i + 1, "tokens_used": worker_tokens},
        })

    return subtask_outputs


async def _validate_output(task: Any, manager: Any, plan: str, subtask_outputs: dict[str, str]) -> str:
    """Have the manager validate subtask outputs."""
    from app.core.collaboration.constants import TASK_TIMEOUT

    validation_prompt = build_manager_validation_prompt(task.description, plan, subtask_outputs)
    try:
        async with __import__("asyncio").timeout(TASK_TIMEOUT):
            manager_validation, _ = await run_agent_simple(
                agent_id=manager.agent_id,
                provider=manager.model_provider or "openai",
                model_id=manager.model_id or "gpt-4o",
                api_key=resolve_api_key(manager.model_provider, manager.api_key_encrypted),
                base_url=resolve_base_url(manager.model_provider, None),
                system_prompt=build_manager_prompt(task.description),
                user_message=validation_prompt,
                tools=manager.tools or [],
            )
        return manager_validation
    except Exception as e:
        logger.error("manager_validation_failed", task_id=task.id, error=str(e))
        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_validate",
            "data": {"content": f"Validation error: {e}", "tokens_used": 0},
        })
        return f"Validation error: {e}"
