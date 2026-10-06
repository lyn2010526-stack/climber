"""Hierarchical process implementation for group collaboration."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, cast

import structlog
from sqlalchemy import select

from app.core.collaboration import agent_runner
from app.core.collaboration.callbacks import invoke_step_callback, invoke_task_callback
from app.core.collaboration.memory import store_memory
from app.core.collaboration.prompts import (
    build_manager_planning_prompt,
    build_manager_prompt,
    build_manager_validation_prompt,
    build_worker_prompt,
    parse_review_result,
)
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupMember, AgentGroupTask

logger = structlog.get_logger(__name__)


async def run_hierarchical_process(task: Any, group: Any, principal: Any = None) -> None:
    """Hierarchical execution: manager agent delegates and validates.

    Args:
        task: The task entity to execute.
        group: The group entity (used to resolve the execution principal).
        principal: Explicit principal propagated to every agent call; resolved
            from the group owner when omitted.

    Raises:
        RuntimeError: When manager/worker selection or any agent call fails,
            so ``run_task`` marks the task failed.
    """
    principal = principal or agent_runner.principal_for_group(group)
    manager_member = await _find_manager(group)
    if not manager_member:
        logger.error("no_manager_found", group_id=group.id)
        raise RuntimeError("No manager found for hierarchical task")

    workers = [
        m
        for m in group.members
        if m.id != manager_member.id and m.role in ("worker", "executor", "participant")
    ]
    if not workers:
        logger.error("no_workers_found", group_id=group.id)
        raise RuntimeError("No workers found for hierarchical task")

    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "manager_start",
            "data": {"member_id": manager_member.id, "member_name": manager_member.agent_id},
        },
    )

    manager_plan = await _plan_subtasks(task, manager_member, group.members, principal=principal)

    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "hierarchical_plan",
            "data": {"content": manager_plan, "tokens_used": 0},
        },
    )

    reviewers = [m for m in group.members if m.role == "reviewer"] or [manager_member]
    revision_context = manager_plan
    for current_round in range(1, max(1, task.max_rounds or 5) + 1):
        task.current_round = current_round
        subtask_outputs = await _delegate_subtasks(
            task, workers, revision_context, principal=principal
        )
        all_issues = []
        for reviewer in reviewers:
            manager_validation = await _validate_output(
                task, reviewer, manager_plan, subtask_outputs, principal=principal
            )
            _, issues = parse_review_result(manager_validation)
            all_issues.extend(issues)
        passed = not all_issues
        if passed:
            break
        revision_context = (
            manager_plan
            + "\nPrevious outputs:\n"
            + json.dumps(subtask_outputs, ensure_ascii=False)
            + "\nIssues to fix:\n"
            + json.dumps(all_issues, ensure_ascii=False)
        )
    final_output = "\n\n".join(subtask_outputs.values())

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "completed" if passed else "partial"
            t.current_round = current_round
            t.final_output = final_output
            t.completed_at = datetime.now(UTC)
            await db.commit()

    await store_memory(
        task.group_id, task.id, cast(str, manager_member.agent_id), final_output, "task_result"
    )
    await invoke_task_callback(task, final_output)

    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "task_completed" if passed else "task_partial",
            "data": {
                "task_id": task.id,
                "final_output": final_output,
                "manager_validation": manager_validation,
            },
        },
    )


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
            (
                await db.execute(
                    select(AgentGroupMember).where(
                        AgentGroupMember.group_id == group.id,
                        AgentGroupMember.role.in_(["manager", "planner", "coordinator"]),
                    )
                )
            )
            .scalars()
            .all()
        )
        return (
            min(
                candidates,
                key=lambda m: ({"manager": 0, "planner": 1, "coordinator": 2}[m.role], m.id),
            )
            if candidates
            else None
        )


async def _plan_subtasks(task: Any, manager: Any, members: list[Any], principal: Any = None) -> str:
    """Have the manager plan subtasks.

    Args:
        task: The task entity.
        manager: The manager member.
        members: All group members (excluded from the planning context).
        principal: Explicit principal for the agent call.

    Returns:
        The manager's plan text.

    Raises:
        RuntimeError: If planning fails or returns an empty plan.
    """
    from app.core.collaboration.constants import TASK_TIMEOUT

    other_members = [m for m in members or [] if m.id != manager.id]
    subtask_prompt = build_manager_planning_prompt(task.description, other_members)
    try:
        async with asyncio.timeout(TASK_TIMEOUT):
            manager_plan, _ = await agent_runner.run_agent_simple(
                agent_id=manager.agent_id,
                provider=manager.model_provider or "openai",
                model_id=manager.model_id or "gpt-4o",
                api_key=resolve_api_key(manager.model_provider, manager.api_key_encrypted),
                base_url=resolve_base_url(manager.model_provider, None),
                system_prompt=build_manager_prompt(task.description),
                user_message=subtask_prompt,
                tools=manager.tools or [],
                group_id=task.group_id,
                role="manager",
                principal=principal,
                task_name=task.description,
            )
        if not manager_plan.strip():
            raise ValueError("Manager returned an empty plan")
        return manager_plan
    except Exception as e:
        logger.error("manager_failed", task_id=task.id, error=str(e))
        raise RuntimeError(f"Manager planning failed: {e}") from e


async def _delegate_subtasks(
    task: Any, workers: list[Any], manager_plan: str, principal: Any = None
) -> dict[str, str]:
    """Delegate subtasks to workers and collect outputs.

    Args:
        task: The task entity.
        workers: The worker members.
        manager_plan: The manager's plan text.
        principal: Explicit principal for every worker call.

    Returns:
        A dict mapping worker IDs to their outputs.

    Raises:
        RuntimeError: Propagated from ``agent_runner.run_agent_with_retry``
            when a worker exhausts retries and fallback.
    """
    subtask_outputs: dict[str, str] = {}
    for i, worker in enumerate(workers):
        subtask_desc = f"{task.description}\n\nContext from manager: {manager_plan}\n"
        if i > 0 and subtask_outputs:
            previous = list(subtask_outputs.values())[-1]
            subtask_desc += f"\nPrevious subtask output: {previous}\n"

        await group_ws_hub.broadcast(
            task.group_id,
            {
                "type": "hierarchical_delegate",
                "data": {
                    "worker_id": worker.id,
                    "worker_name": worker.agent_id,
                    "subtask_index": i + 1,
                },
            },
        )

        worker_output, worker_tokens = await agent_runner.run_agent_with_retry(
            agent_id=worker.agent_id,
            provider=worker.model_provider or "openai",
            model_id=worker.model_id or "gpt-4o",
            api_key=resolve_api_key(worker.model_provider, worker.api_key_encrypted),
            system_prompt=build_worker_prompt(subtask_desc),
            user_message=subtask_desc,
            tools=worker.tools or [],
            group_id=task.group_id,
            role="worker",
            base_url=resolve_base_url(worker.model_provider, None),
            principal=principal,
            task_name=task.description,
        )
        subtask_outputs[worker.id] = worker_output

        await invoke_step_callback(task, "worker", worker.agent_id, worker_output)

        await group_ws_hub.broadcast(
            task.group_id,
            {
                "type": "hierarchical_delegate_done",
                "data": {
                    "worker_id": worker.id,
                    "worker_name": worker.agent_id,
                    "subtask_index": i + 1,
                    "tokens_used": worker_tokens,
                },
            },
        )

    return subtask_outputs


async def _validate_output(
    task: Any, manager: Any, plan: str, subtask_outputs: dict[str, str], principal: Any = None
) -> str:
    """Have the manager validate subtask outputs.

    Args:
        task: The task entity.
        manager: The manager member.
        plan: The manager's plan text.
        subtask_outputs: Worker outputs keyed by worker ID.
        principal: Explicit principal for the agent call.

    Returns:
        The manager's validation output.

    Raises:
        RuntimeError: If validation fails.
    """
    from app.core.collaboration.constants import TASK_TIMEOUT

    validation_prompt = build_manager_validation_prompt(task.description, plan, subtask_outputs)
    try:
        async with asyncio.timeout(TASK_TIMEOUT):
            manager_validation, _ = await agent_runner.run_agent_simple(
                agent_id=manager.agent_id,
                provider=manager.model_provider or "openai",
                model_id=manager.model_id or "gpt-4o",
                api_key=resolve_api_key(manager.model_provider, manager.api_key_encrypted),
                base_url=resolve_base_url(manager.model_provider, None),
                system_prompt=build_manager_prompt(task.description),
                user_message=validation_prompt,
                tools=manager.tools or [],
                group_id=task.group_id,
                role="reviewer" if manager.role == "reviewer" else "manager",
                principal=principal,
                task_name=task.description,
            )
        return manager_validation
    except Exception as e:
        logger.error("manager_validation_failed", task_id=task.id, error=str(e))
        raise RuntimeError(f"Manager validation failed: {e}") from e
