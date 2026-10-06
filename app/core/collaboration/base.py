"""Main GroupCollaborationEngine facade.

Orchestrates multi-agent collaboration with multiple process types.
Enhanced with CrewAI/AutoGen patterns:
- Task chaining and context passing
- Sequential, hierarchical, and group_chat processes
- Guardrails and output validation
- Checkpoint/resume
- Memory persistence
- Callbacks
- Human-in-the-loop
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.collaboration import agent_runner
from app.core.collaboration.agent_runner import principal_for_group, run_agent_with_retry
from app.core.collaboration.checkpoint import load_latest_checkpoint, resume_from_checkpoint
from app.core.collaboration.constants import TASK_TIMEOUT
from app.core.collaboration.group_chat import run_group_chat_process
from app.core.collaboration.hierarchical import run_hierarchical_process
from app.core.collaboration.memory import inject_memory, store_memory
from app.core.collaboration.prompts import (
    build_reviewer_prompt,
    build_worker_prompt,
    parse_review_result,
)
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.collaboration.sequential import run_sequential_process
from app.core.di import resolve as di_resolve
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask

logger = structlog.get_logger(__name__)


class GroupCollaborationEngine:
    """Orchestrates multi-agent collaboration with multiple process types."""

    def __init__(
        self,
        model_registry: Any,
        tool_registry: Any,
        max_concurrent_tasks: int | None = None,
    ) -> None:
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self._max_concurrent = (
            settings.max_concurrent_subtasks
            if max_concurrent_tasks is None
            else max_concurrent_tasks
        )
        self._task_semaphore = asyncio.Semaphore(self._max_concurrent)
        self._review_states: dict[str, dict[str, str]] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def _run_sequential_process(
        self,
        task: Any,
        worker: Any,
        reviewers: list[Any],
        group: Any,
        max_rounds: int | None = None,
        checkpoint: Any = None,
        principal: Any = None,
    ) -> None:
        """Run the sequential collaboration process for a task."""
        await run_sequential_process(
            task,
            worker,
            reviewers,
            group,
            max_rounds or task.max_rounds or 5,
            checkpoint=checkpoint,
            principal=principal,
        )

    async def _run_agent_simple(
        self,
        agent_id: str,
        provider: str,
        model_id: str,
        api_key: str,
        system_prompt: str,
        user_message: str,
        tools: list[str],
        base_url: str | None = None,
        principal: Any = None,
    ) -> tuple[str, int]:
        """Run a single agent turn."""
        from app.core.collaboration.agent_runner import run_agent_simple as _run_agent_simple_fn

        return await _run_agent_simple_fn(
            agent_id,
            provider,
            model_id,
            api_key,
            system_prompt,
            user_message,
            tools,
            base_url,
            principal,
        )

    async def _run_agent_with_retry(
        self,
        agent_id: str,
        provider: str,
        model_id: str,
        api_key: str,
        system_prompt: str,
        user_message: str,
        tools: list[str],
        group_id: str,
        role: str = "worker",
        base_url: str | None = None,
        principal: Any = None,
    ) -> tuple[str, int]:
        """Run agent with retry via the shared agent_runner implementation.

        Retry, timeout, fallback and failure semantics (RuntimeError after the
        final attempt) are owned by ``agent_runner.run_agent_with_retry``; this
        method only forwards so there is a single source of truth.
        """
        return await run_agent_with_retry(
            agent_id=agent_id,
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            system_prompt=system_prompt,
            user_message=user_message,
            tools=tools,
            group_id=group_id,
            role=role,
            base_url=base_url,
            principal=principal,
        )

    async def _load_latest_checkpoint(self, task_id: str) -> Any:
        """Load the latest checkpoint for a task."""
        return await load_latest_checkpoint(task_id)

    async def _resume_from_checkpoint(self, task: Any, checkpoint: Any) -> None:
        """Resume task execution from a checkpoint."""
        await resume_from_checkpoint(task, checkpoint)

    async def run_task(self, task_id: str) -> None:
        """Execute a group task using the group's configured process type.

        Args:
            task_id: The task ID to execute.
        """
        db_task = None
        db_worker = None
        db_reviewers = []
        db_group = None

        current_task = asyncio.current_task()
        self._running_tasks[task_id] = current_task
        try:
            try:
                db_task, db_worker, db_reviewers, db_group = await _load_task_context(task_id)
                if db_task is None or db_worker is None or db_group is None:
                    return
            except Exception as e:
                logger.error("db_error_loading_task", task_id=task_id, error=str(e))
                return

            task = db_task
            worker = db_worker
            reviewers = db_reviewers
            group = db_group

            principal = principal_for_group(group)
            checkpoint = await self._load_latest_checkpoint(task_id)
            if checkpoint and checkpoint.status in ("running", "paused"):
                logger.info("resuming_from_checkpoint", task_id=task_id, checkpoint_id=checkpoint.id)
                await self._resume_from_checkpoint(task, checkpoint)
                await _dispatch_by_process_type(
                    self, task, worker, reviewers, group, checkpoint=checkpoint, principal=principal,
                )
                return

            await _dispatch_by_process_type(self, task, worker, reviewers, group, principal=principal)

        except asyncio.CancelledError:
            logger.info("task_cancelled", task_id=task_id)
            await _update_task_status(task_id, "stopped")
            raise
        except Exception as e:
            logger.exception("group_task_failed", task_id=task_id)
            await _update_task_status(task_id, "failed")
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_failed",
                "data": {"task_id": task_id, "error": str(e)},
            })
        finally:
            self._running_tasks.pop(task_id, None)

    async def run_group_tasks(self, group_id: str) -> dict[str, Any]:
        """Execute all pending tasks in a group using DAG-based dependency resolution.

        Args:
            group_id: The group ID to execute tasks for.

        Returns:
            A dictionary with execution results.
        """
        async with async_session() as db:
            group = (await db.execute(select(AgentGroup).where(AgentGroup.id == group_id))).scalar_one_or_none()
            if not group:
                return {"error": "Group not found"}

            tasks = (
                await db.execute(
                    select(AgentGroupTask)
                    .where(AgentGroupTask.group_id == group_id)
                    .where(AgentGroupTask.status.in_(["pending", "running"]))
                )
            ).scalars().all()

        if not tasks:
            return {"status": "no_pending_tasks"}

        from app.core.collaboration.deadlock import (
            deadlocked_task_ids,
            detect_deadlock,
            topological_order,
        )

        dependency_map = {t.id: list(t.dependencies or []) for t in tasks}
        deadlock_cycles = detect_deadlock(dependency_map)
        if deadlock_cycles:
            logger.warning("deadlock_detected_in_group_tasks", group_id=group_id, cycles=deadlock_cycles)
            blocked = deadlocked_task_ids(dependency_map)
            if all(t.id in blocked for t in tasks):
                return {
                    "status": "deadlock",
                    "error": f"Cycle detected in task dependencies: {deadlock_cycles}",
                    "cycles": deadlock_cycles,
                }
            logger.warning("deadlock_skipping_blocked_tasks", group_id=group_id, blocked=sorted(blocked))

        task_map: dict[str, AgentGroupTask] = {t.id: t for t in tasks}
        execution_levels = topological_order(dependency_map)
        results: dict[str, Any] = {"status": "completed", "levels": []}
        completed_tasks: set[str] = set()

        for level in execution_levels:
            level_results = []
            for task_id in level:
                task = task_map.get(task_id)
                if not task:
                    continue
                if any(dep in task_map and dep not in completed_tasks for dep in task.dependencies or []):
                    await _update_task_status(task_id, "failed")
                    level_results.append({"task_id": task_id, "status": "failed", "error": "Dependency did not complete"})
                    results["status"] = "partial"
                    continue

                context_data: dict[str, str] = {}
                for dep_id in (task.dependencies or []):
                    if dep_id in completed_tasks and dep_id in task_map:
                        dep_task = task_map[dep_id]
                        if dep_task.final_output:
                            context_data[dep_id] = dep_task.final_output

                await group_ws_hub.broadcast(group_id, {
                    "type": "dag_level_start",
                    "data": {"task_id": task_id, "level": len(results["levels"]) + 1},
                })

                try:
                    await self._run_single_task_in_dag(task, group, context_data)
                    async with async_session() as db:
                        saved = await db.get(AgentGroupTask, task_id)
                        status = saved.status if saved else "failed"
                        task.final_output = saved.final_output if saved else None
                    if status == "completed":
                        completed_tasks.add(task_id)
                    else:
                        results["status"] = "partial"
                    level_results.append({"task_id": task_id, "status": status})
                except Exception as e:
                    await _update_task_status(task_id, "failed")
                    results["status"] = "partial"
                    logger.error("dag_task_failed", task_id=task_id, error=str(e))
                    level_results.append({"task_id": task_id, "status": "failed", "error": str(e)})

            results["levels"].append(level_results)

        return results

    async def _run_single_task_in_dag(
        self,
        task: AgentGroupTask,
        group: AgentGroup,
        context_data: dict[str, str],
    ) -> None:
        """Execute a single task within a DAG context.

        Args:
            task: The task to execute.
            group: The group the task belongs to.
            context_data: Context from completed dependencies.
        """
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if not t:
                return
            t.status = "running"
            t.started_at = datetime.now(UTC)
            await db.commit()
            task = t

        worker = await _select_worker(task)
        if not worker:
            raise Exception("No worker available")

        principal = principal_for_group(group)
        memory_context = await inject_memory(task.group_id, task.id, task.description)
        context_parts = [memory_context]
        if context_data:
            ctx_str = "\n\n".join(f"[Task {k} output]:\n{v}" for k, v in context_data.items())
            context_parts.insert(0, ctx_str)

        worker_output, worker_tokens = await run_agent_with_retry(
            agent_id=worker.agent_id,
            provider=worker.model_provider or "openai",
            model_id=worker.model_id or "gpt-4o",
            api_key=resolve_api_key(worker.model_provider, worker.api_key_encrypted),
            system_prompt=build_worker_prompt(task.description),
            user_message=task.description + "\n\nContext:\n" + "\n".join(context_parts),
            tools=worker.tools or [],
            group_id=task.group_id,
            role="worker",
            base_url=resolve_base_url(worker.model_provider, None),
            principal=principal,
            task_name=task.description,
        )

        final_output = worker_output
        reviewers = await _load_reviewers(task)
        all_issues = []
        review_tokens = 0
        for reviewer in reviewers:
            try:
                async with asyncio.timeout(TASK_TIMEOUT):
                    review_output, tokens = await agent_runner.run_agent_simple(
                        agent_id=reviewer.agent_id,
                        provider=reviewer.model_provider or "openai",
                        model_id=reviewer.model_id or "gpt-4o",
                        api_key=resolve_api_key(reviewer.model_provider, reviewer.api_key_encrypted),
                        system_prompt=build_reviewer_prompt(task.description),
                        user_message=f"Review this output:\n{worker_output}",
                        tools=reviewer.tools or [],
                        group_id=task.group_id,
                        role="reviewer",
                        base_url=resolve_base_url(reviewer.model_provider, None),
                        principal=principal,
                        task_name=task.description,
                    )
            except Exception:
                await _update_task_status(task.id, "failed")
                raise
            review_tokens += tokens
            _, issues = parse_review_result(review_output)
            all_issues.extend(issues)
        passed = not all_issues

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                t.status = "completed" if passed else "partial"
                t.final_output = final_output
                t.total_tokens = (t.total_tokens or 0) + worker_tokens + review_tokens
                t.completed_at = datetime.now(UTC)
                await db.commit()

        if passed:
            await store_memory(task.group_id, task.id, worker.agent_id, final_output, "task_result")
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed" if passed else "task_partial",
            "data": {"task_id": task.id, "output": final_output, "issues": all_issues},
        })

    async def handoff_task(self, task_id: str, target_agent_id: str, reason: str = "") -> dict[str, Any]:
        """Hand off a task from one agent to another.

        Args:
            task_id: The task ID to hand off.
            target_agent_id: The target agent ID.
            reason: Optional reason for the handoff.

        Returns:
            A dictionary with handoff details.
        """
        from app.core.collaboration.handoff import HandoffMessage

        async with async_session() as db:
            task = await db.get(AgentGroupTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            target = (
                await db.execute(
                    select(AgentGroupMember).where(
                        AgentGroupMember.agent_id == target_agent_id,
                        AgentGroupMember.group_id == task.group_id,
                    )
                )
            ).scalar_one_or_none()
            if not target:
                raise HTTPException(status_code=404, detail="Target agent not found")

            source_worker_id = task.worker_id or ""
            task.worker_id = target.id
            await db.commit()

            msg = HandoffMessage(
                source_agent=source_worker_id,
                target_agent=target.id,
                task_id=task_id,
                context=task.description,
                reason=reason,
            )

            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_handoff",
                "data": {
                    "task_id": task_id,
                    "from_agent": msg.source_agent,
                    "to_agent": target.id,
                    "reason": reason,
                },
            })

            return {"ok": True, "task_id": task_id, "handoff_to": target.id}

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task by its ID.

        Args:
            task_id: The task ID to cancel.

        Returns:
            True if task was found and cancelled, False otherwise.
        """
        task = self._running_tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        return True

    def get_review_state(self, task_id: str, reviewer_id: str) -> str:
        """Get the review state for a reviewer on a task.

        Args:
            task_id: The task ID.
            reviewer_id: The reviewer ID.

        Returns:
            The review state string, defaults to 'pending'.
        """
        return self._review_states.get(task_id, {}).get(reviewer_id, "pending")

    def set_review_state(self, task_id: str, reviewer_id: str, state: str) -> None:
        """Set the review state for a reviewer on a task.

        Args:
            task_id: The task ID.
            reviewer_id: The reviewer ID.
            state: The state to set.
        """
        if task_id not in self._review_states:
            self._review_states[task_id] = {}
        self._review_states[task_id][reviewer_id] = state

    def get_task_review_summary(self, task_id: str) -> dict[str, int]:
        """Get a summary of review states for a task.

        Args:
            task_id: The task ID.

        Returns:
            A dictionary counting reviewers in each state.
        """
        states = self._review_states.get(task_id, {})
        summary: dict[str, int] = {"pending": 0, "approved": 0, "rejected": 0}
        for s in states.values():
            summary[s] = summary.get(s, 0) + 1
        return summary


async def _load_task_context(task_id: str) -> tuple:
    """Load task, worker, reviewers, and group from database.

    Args:
        task_id: The task ID to load.

    Returns:
        A tuple of (task, worker, reviewers, group) or Nones on failure.
    """
    async with async_session() as db:
        task = (await db.execute(select(AgentGroupTask).where(AgentGroupTask.id == task_id))).scalar_one_or_none()
        if task is None:
            logger.error("task_not_found", task_id=task_id)
            return None, None, None, None

        group = (
            await db.execute(
                select(AgentGroup)
                .options(selectinload(AgentGroup.members))
                .where(AgentGroup.id == task.group_id)
            )
        ).scalar_one_or_none()
        if group is None:
            logger.error("group_not_found", group_id=task.group_id)
            return None, None, None, None

        worker = None
        if task.worker_id:
            worker = (
                await db.execute(select(AgentGroupMember).where(AgentGroupMember.id == task.worker_id))
            ).scalar_one_or_none()

        if worker is None:
            worker = (
                await db.execute(select(AgentGroupMember).where(AgentGroupMember.group_id == task.group_id))
            ).scalars().first()
        if worker is None:
            logger.error("worker_not_found", task_id=task_id, worker_id=task.worker_id)
            task.status = "failed"
            await db.commit()
            return None, None, None, None

        reviewers = (
            await db.execute(select(AgentGroupMember).where(AgentGroupMember.id.in_(task.reviewer_ids or [])))
        ).scalars().all()

        task.started_at = datetime.now(UTC)
        task.status = "running"
        await db.commit()

        return task, worker, list(reviewers), group


async def _dispatch_by_process_type(
    engine: GroupCollaborationEngine,
    task: Any,
    worker: Any,
    reviewers: list[Any],
    group: Any,
    checkpoint: Any = None,
    principal: Any = None,
) -> None:
    """Dispatch task execution based on the group's process type.

    Args:
        engine: The collaboration engine instance.
        task: The task to execute.
        worker: The assigned worker.
        reviewers: List of reviewers.
        group: The group entity.
        checkpoint: Optional checkpoint to resume from.
        principal: Explicit principal propagated to every agent call.
    """
    process_type = group.process_type or "sequential"
    if process_type == "sequential":
        await engine._run_sequential_process(
            task,
            worker,
            reviewers,
            group,
            task.max_rounds or 5,
            checkpoint=checkpoint,
            principal=principal,
        )
    elif process_type == "hierarchical":
        await run_hierarchical_process(task, group, principal=principal)
    elif process_type == "group_chat":
        await run_group_chat_process(task, group, principal=principal)
    else:
        logger.error("unknown_process_type", process_type=process_type, task_id=task.id)
        await _update_task_status(task.id, "failed")
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_failed",
            "data": {"task_id": task.id, "error": f"Unknown process type: {process_type}"},
        })


async def _update_task_status(task_id: str, status: str) -> None:
    """Update task status in database.

    Args:
        task_id: The task ID.
        status: The new status.
    """
    try:
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task_id)
            if t:
                t.status = status
                await db.commit()
    except Exception:
        pass


async def _select_worker(task: Any) -> Any | None:
    """Select a worker for a task.

    Args:
        task: The task entity.

    Returns:
        The selected worker member or None.
    """
    if task.worker_id:
        async with async_session() as db:
            worker = (
                await db.execute(select(AgentGroupMember).where(AgentGroupMember.id == task.worker_id))
            ).scalar_one_or_none()
            if worker:
                return worker

    async with async_session() as db:
        worker = (
            await db.execute(
                select(AgentGroupMember)
                .where(AgentGroupMember.group_id == task.group_id)
                .where(AgentGroupMember.role.in_(["worker", "participant"]))
            )
        ).scalars().first()
    return worker


async def _load_reviewers(task: Any) -> list[Any]:
    """Load reviewers for a task.

    Args:
        task: The task entity.

    Returns:
        List of reviewer members.
    """
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            reviewers = (
                await db.execute(select(AgentGroupMember).where(AgentGroupMember.id.in_(t.reviewer_ids or [])))
            ).scalars().all()
            return list(reviewers)
    return []


_group_collaboration_engine: GroupCollaborationEngine | None = None


@dataclass
class CollaborationTask:
    """A task to be executed by the group."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollaborationResult:
    """Result of a group collaboration task."""

    task_id: str = ""
    status: str = "pending"
    output: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def get_group_collaboration_engine() -> GroupCollaborationEngine:
    """Get or create the global GroupCollaborationEngine singleton.

    Returns:
        The GroupCollaborationEngine instance.
    """
    global _group_collaboration_engine
    if _group_collaboration_engine is None:
        try:
            model_registry = di_resolve("ModelRegistry")
        except KeyError:
            from app.models.registry import ModelRegistry
            model_registry = ModelRegistry()
        _group_collaboration_engine = GroupCollaborationEngine(
            model_registry=model_registry,
            tool_registry=__import__("app.tools", fromlist=["ToolRegistry"]).ToolRegistry(),
        )
    return _group_collaboration_engine
