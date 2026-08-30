"""Group collaboration engine: supports sequential, hierarchical, and group_chat processes.

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
import importlib
import json
import os
import re
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from fastapi import HTTPException
from sqlalchemy import select, update

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine
from app.core.api_key_crypto import decrypt_api_key
from app.core.di import resolve as di_resolve
from app.core.group_ws_hub import group_ws_hub
from app.core.task_dag import HandoffMessage, TaskDAG, TaskNode
from app.models.registry import ModelRegistry
from app.storage import async_session
from app.storage.models_groups import (
    AgentGroup,
    AgentGroupMember,
    AgentGroupMemory,
    AgentGroupTask,
    AgentGroupTaskCheckpoint,
)

logger = structlog.get_logger(__name__)

def _resolve_api_key(provider: str, stored_key: str | None) -> str:
    """Resolve API key from member config or environment variable fallback."""
    if stored_key:
        return decrypt_api_key(stored_key)
    env_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "stepfun": "STEPFUN_API_KEY",
        "ollama": "",
    }
    var = env_map.get(provider.lower())
    if var:
        return os.environ.get(var, "")
    return ""

def _resolve_base_url(provider: str, stored_url: str | None) -> str | None:
    """Resolve base_url from member config or environment variable fallback."""
    if stored_url:
        return stored_url
    env_map = {
        "stepfun": "STEPFUN_BASE_URL",
        "ollama": "OLLAMA_BASE_URL",
    }
    var = env_map.get(provider.lower())
    return os.environ.get(var) if var else None

# Task execution timeout (seconds)
TASK_TIMEOUT = 300
MAX_RETRIES = 2

# Model fallback mapping for degradation
FALLBACK_MODELS: dict[str, tuple[str, str]] = {
    "gpt-4o": ("openai", "gpt-4o-mini"),
    "claude-3-5-sonnet": ("anthropic", "claude-3-haiku"),
    "gemini-1.5-pro": ("google", "gemini-1.5-flash"),
    "step-2": ("stepfun", "step-1-8k"),
}

# Registry for Python callable callbacks (step and task callbacks)
# Maps a string reference to a callable. Populated by the application.
CALLBACK_REGISTRY: dict[str, Callable[..., Any]] = {}

# Lease TTL and heartbeat cadence for cross-instance crash recovery.
LEASE_TTL_SECONDS = 60.0
LEASE_HEARTBEAT_SECONDS = 15.0


@dataclass(frozen=True)
class TaskLease:
    """Immutable handle for the current execution generation of a task."""

    task_id: str
    owner: str
    token: int
    expires_at: datetime


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _db_now() -> datetime:
    """Return naive UTC matching the database DateTime representation."""
    return _utcnow().replace(tzinfo=None)


def register_callback(name: str, fn: Callable[..., Any]) -> None:
    """Register a named callback for use as step_callback or task_callback."""
    CALLBACK_REGISTRY[name] = fn


# Background recovery tasks, kept referenced to avoid GC.
_BACKGROUND_RECOVERY_TASKS: set[asyncio.Task] = set()


class GroupCollaborationEngine:
    """Orchestrates multi-agent collaboration with multiple process types."""

    def __init__(self, model_registry: ModelRegistry, tool_registry: Any, max_concurrent_tasks: int = 10) -> None:
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self._max_concurrent = max_concurrent_tasks
        self._task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._review_states: dict[str, dict[str, str]] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self.instance_id: str = f"{uuid.uuid4()}"

    async def _claim_lease(
        self,
        task_id: str,
        *,
        status: str = "pending",
        takeover: bool = False,
    ) -> TaskLease | None:
        """Atomically claim execution rights for a task.

        Normal claim transitions ``pending -> running``. With ``takeover=True``
        an expired lease on a ``running`` task may be reclaimed by a new owner
        with a strictly higher fencing token.
        """
        now = _db_now()
        expires_at = now + timedelta(seconds=LEASE_TTL_SECONDS)
        stmt = (
            update(AgentGroupTask)
            .where(AgentGroupTask.id == task_id)
            .values(
                lease_token=AgentGroupTask.lease_token + 1,
                lease_owner=self.instance_id,
                lease_expires_at=expires_at,
            )
        )
        if takeover and status == "running":
            stmt = stmt.where(
                AgentGroupTask.status.in_(("running", "awaiting_human_review")),
                AgentGroupTask.lease_expires_at.is_(None)
                | (AgentGroupTask.lease_expires_at < now),
            ).values(status="running")
        else:
            stmt = stmt.where(AgentGroupTask.status == status)
            if status == "pending":
                stmt = stmt.values(status="running", started_at=now)
        async with async_session() as db:
            token = (await db.execute(stmt.returning(AgentGroupTask.lease_token))).scalar_one_or_none()
            if token is None:
                await db.rollback()
                return None
            await db.commit()
        return TaskLease(
            task_id=task_id,
            owner=self.instance_id,
            token=int(token),
            expires_at=expires_at,
        )

    async def _renew_lease(self, task_id: str, token: int) -> bool:
        """Heartbeat: extend the lease only if this generation still owns it."""
        async with async_session() as db:
            renew = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .where(AgentGroupTask.status.in_(("running", "awaiting_human_review")))
                .where(AgentGroupTask.lease_owner == self.instance_id)
                .where(AgentGroupTask.lease_token == token)
                .where(AgentGroupTask.lease_expires_at >= _db_now())
                .values(lease_expires_at=_db_now() + timedelta(seconds=LEASE_TTL_SECONDS))
            )
            if renew.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
        return True

    async def _update_progress(self, task_id: str, token: int, **values: Any) -> bool:
        """Write progress fields (e.g. current_round) guarded by lease token."""
        async with async_session() as db:
            progress = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .where(AgentGroupTask.status == "running")
                .where(AgentGroupTask.lease_owner == self.instance_id)
                .where(AgentGroupTask.lease_token == token)
                .where(AgentGroupTask.lease_expires_at >= _db_now())
                .values(**values)
            )
            if progress.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
        return True

    async def _complete_running_task(self, task_id: str, token: int, *, status: str, **values: Any) -> bool:
        """Terminal state transition guarded by lease token fencing."""
        async with async_session() as db:
            completion = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .where(AgentGroupTask.status == "running")
                .where(AgentGroupTask.lease_owner == self.instance_id)
                .where(AgentGroupTask.lease_token == token)
                .where(AgentGroupTask.lease_expires_at >= _db_now())
                .values(status=status, lease_owner=None, lease_expires_at=None, completed_at=_utcnow(), **values)
            )
            if completion.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
        return True

    async def _task_is_running(self, task_id: str, token: int | None = None) -> bool:
        async with async_session() as db:
            stmt = select(AgentGroupTask.id).where(
                AgentGroupTask.id == task_id,
                AgentGroupTask.status == "running",
            )
            if token is not None:
                stmt = stmt.where(
                    AgentGroupTask.lease_owner == self.instance_id,
                    AgentGroupTask.lease_token == token,
                    AgentGroupTask.lease_expires_at >= _db_now(),
                )
            return (await db.execute(stmt)).scalar_one_or_none() is not None

    async def _fail_running_task(self, task_id: str, token: int | None = None) -> bool:
        async with async_session() as db:
            stmt = (
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task_id)
                .where(AgentGroupTask.status == "running")
                .values(status="failed", lease_owner=None, lease_expires_at=None, completed_at=datetime.now(UTC))
            )
            if token is not None:
                stmt = stmt.where(
                    AgentGroupTask.lease_owner == self.instance_id,
                    AgentGroupTask.lease_token == token,
                    AgentGroupTask.lease_expires_at >= _db_now(),
                )
            failure = await db.execute(stmt)
            if failure.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
        return True

    async def _claim_or_takeover(self, task_id: str) -> TaskLease | None:
        """Claim a pending task, or take over a running task whose lease expired."""
        lease = await self._claim_lease(task_id)
        if lease is None:
            lease = await self._claim_lease(task_id, status="running", takeover=True)
        return lease

    async def run_task(self, task_id: str) -> None:
        """Execute a group task using the group's configured process type."""
        db_task = None
        db_worker = None
        db_reviewers = []
        db_group = None

        # Register the running task for cancellation support
        current_task = asyncio.current_task()
        running_task = self._running_tasks.get(task_id)
        if running_task is not None and not running_task.done():
            logger.info("task_already_running", task_id=task_id)
            return
        if current_task is None:
            logger.error("task_missing_asyncio_context", task_id=task_id)
            return
        self._running_tasks[task_id] = current_task
        try:
            try:
                async with async_session() as db:
                    task = (
                        await db.execute(
                            select(AgentGroupTask).where(AgentGroupTask.id == task_id)
                        )
                    ).scalar_one_or_none()
                    if task is None:
                        logger.error("task_not_found", task_id=task_id)
                        return

                    claim_now = _db_now()
                    claim = await db.execute(
                        update(AgentGroupTask)
                        .where(AgentGroupTask.id == task_id)
                        .where(
                            (AgentGroupTask.status == "pending")
                            | (
                                AgentGroupTask.status.in_(("running", "awaiting_human_review"))
                                & (
                                    AgentGroupTask.lease_expires_at.is_(None)
                                    | (AgentGroupTask.lease_expires_at < claim_now)
                                )
                            )
                        )
                        .values(
                            status="running",
                            started_at=claim_now,
                            lease_token=AgentGroupTask.lease_token + 1,
                            lease_owner=self.instance_id,
                            lease_expires_at=claim_now + timedelta(seconds=LEASE_TTL_SECONDS),
                        )
                        .returning(AgentGroupTask.lease_token)
                    )
                    claimed_token = claim.scalar_one_or_none()
                    if claimed_token is None:
                        current_status = task.status
                        await db.rollback()
                        logger.info("task_not_claimed", task_id=task_id, status=current_status)
                        return
                    await db.commit()
                    await db.refresh(task)
                    lease = TaskLease(
                        task_id=task_id,
                        owner=self.instance_id,
                        token=int(claimed_token),
                        expires_at=claim_now + timedelta(seconds=LEASE_TTL_SECONDS),
                    )

                    group = (
                        await db.execute(
                            select(AgentGroup).where(AgentGroup.id == task.group_id)
                        )
                    ).scalar_one_or_none()
                    if group is None:
                        logger.error("group_not_found", group_id=task.group_id)
                        await db.execute(
                            update(AgentGroupTask)
                            .where(AgentGroupTask.id == task_id)
                            .where(AgentGroupTask.status == "running")
                            .where(AgentGroupTask.lease_token == lease.token)
                            .values(
                                status="failed",
                                lease_owner=None,
                                lease_expires_at=None,
                                completed_at=_db_now(),
                            )
                        )
                        await db.commit()
                        return
                    db_group = group

                    worker = None
                    if task.worker_id:
                        worker = (
                            await db.execute(
                                select(AgentGroupMember).where(AgentGroupMember.id == task.worker_id)
                            )
                        ).scalar_one_or_none()

                    if worker is None:
                        worker = (
                            await db.execute(
                                select(AgentGroupMember).where(AgentGroupMember.group_id == task.group_id)
                            )
                        ).scalars().first()
                    if worker is None:
                        logger.error("worker_not_found", task_id=task_id, worker_id=task.worker_id)
                        await db.execute(
                            update(AgentGroupTask)
                            .where(AgentGroupTask.id == task_id)
                            .where(AgentGroupTask.status == "running")
                            .where(AgentGroupTask.lease_token == lease.token)
                            .values(
                                status="failed",
                                lease_owner=None,
                                lease_expires_at=None,
                                completed_at=_db_now(),
                            )
                        )
                        await db.commit()
                        return
                    db_worker = worker

                    reviewers = (
                        await db.execute(
                            select(AgentGroupMember).where(
                                AgentGroupMember.id.in_(task.reviewer_ids or [])
                            )
                        )
                    ).scalars().all()
                    db_reviewers = list(reviewers)

                    db_task = task

            except Exception as e:
                logger.error("db_error_loading_task", task_id=task_id, error=str(e))
                return

            if db_task is None or db_worker is None or db_group is None:
                return

            task = db_task
            worker = db_worker
            reviewers = db_reviewers
            group = db_group

            # Check for resume from checkpoint
            checkpoint = await self._load_latest_checkpoint(task_id)
            if checkpoint and checkpoint.status in ("running", "paused"):
                logger.info("resuming_from_checkpoint", task_id=task_id, checkpoint_id=checkpoint.id)
                resumed_task = await self._resume_from_checkpoint(task, checkpoint, token=lease.token)
                if resumed_task is None:
                    return
                task = resumed_task

            # Dispatch based on process type
            process_type = group.process_type or "sequential"
            heartbeat = asyncio.create_task(self._heartbeat_loop(lease))
            try:
                async with self._task_semaphore:
                    if process_type == "sequential":
                        await self._run_sequential_process(task, worker, reviewers, group, lease=lease)
                    elif process_type == "hierarchical":
                        await self._run_hierarchical_process(task, group, lease=lease)
                    elif process_type == "group_chat":
                        await self._run_group_chat_process(task, group, lease=lease)
                    else:
                        logger.error("unknown_process_type", process_type=process_type, task_id=task_id)
                        await self._complete_running_task(task_id, lease.token, status="failed")
            except asyncio.CancelledError:
                logger.info("task_cancelled", task_id=task_id)
                try:
                    await self._complete_running_task(task_id, lease.token, status="stopped")
                except Exception:
                    logger.debug("core.group_collaboration.suppressed", exc_info=True)
                raise
            except Exception as e:
                logger.exception("group_task_failed", task_id=task_id)
                try:
                    if not await self._complete_running_task(task_id, lease.token, status="failed"):
                        return
                except Exception:
                    logger.debug("core.group_collaboration.suppressed", exc_info=True)
                await group_ws_hub.broadcast(task.group_id, {
                    "type": "task_failed",
                    "data": {"task_id": task_id, "error": str(e)},
                })
            finally:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
        finally:
            if self._running_tasks.get(task_id) is current_task:
                self._running_tasks.pop(task_id, None)

    async def _heartbeat_loop(self, lease: TaskLease) -> None:
        """Renew the execution lease until cancelled or ownership is lost."""
        while True:
            await asyncio.sleep(LEASE_HEARTBEAT_SECONDS)
            if not await self._renew_lease(lease.task_id, lease.token):
                logger.warning("task_lease_lost", task_id=lease.task_id, token=lease.token)
                self.cancel_task(lease.task_id)
                return

    async def recover_stale_running_tasks(self) -> int:
        """Re-claim running tasks whose lease expired (e.g. after a crash).

        Only tasks with an expired (or absent) lease are taken over; active
        leases held by live instances are left alone. Paused tasks stay paused
        but get their stale ownership cleared.
        """
        now = _db_now()
        recovered = 0
        async with async_session() as db:
            stale_running = (
                await db.execute(
                    select(AgentGroupTask.id).where(
                        AgentGroupTask.status.in_(("running", "awaiting_human_review")),
                        AgentGroupTask.lease_expires_at.is_(None)
                        | (AgentGroupTask.lease_expires_at < now),
                    )
                )
            ).scalars().all()
            stale_paused = (
                await db.execute(
                    select(AgentGroupTask).where(
                        AgentGroupTask.status == "paused",
                        AgentGroupTask.lease_expires_at.is_(None)
                        | (AgentGroupTask.lease_expires_at < now),
                    )
                )
            ).scalars().all()
            for paused_task in stale_paused:
                paused_task.lease_owner = None
                paused_task.lease_expires_at = None
            await db.commit()
        for task_id in stale_running:
            logger.info("recovering_stale_task", task_id=task_id)
            _task = asyncio.create_task(self.run_task(task_id))
            _BACKGROUND_RECOVERY_TASKS.add(_task)
            _task.add_done_callback(_BACKGROUND_RECOVERY_TASKS.discard)
            recovered += 1
        return recovered

    async def run_group_tasks(self, group_id: str) -> dict[str, Any]:
        """Execute all pending tasks in a group using DAG-based dependency resolution.

        Tasks are grouped into parallel-safe execution levels.
        Within each level, tasks run concurrently.
        """
        async with async_session() as db:
            group = (
                await db.execute(
                    select(AgentGroup).where(AgentGroup.id == group_id)
                )
            ).scalar_one_or_none()
            if not group:
                return {"error": "Group not found"}

            tasks = (
                await db.execute(
                    select(AgentGroupTask)
                    .where(AgentGroupTask.group_id == group_id)
                    .where(AgentGroupTask.status.in_(["pending"]))
                )
            ).scalars().all()

        if not tasks:
            return {"status": "no_pending_tasks"}

        # Build DAG
        dag = TaskDAG()
        task_map: dict[str, AgentGroupTask] = {}
        for t in tasks:
            task_map[t.id] = t
            dag.add_task(TaskNode(
                task_id=t.id,
                name=t.description[:50],
                dependencies=t.dependencies or [],
                payload={"description": t.description, "worker_id": t.worker_id, "reviewer_ids": t.reviewer_ids, "max_rounds": t.max_rounds},
            ))

        # Check for cycles
        cycle = dag.detect_cycle()
        if cycle:
            return {"error": f"Cycle detected in task dependencies: {cycle}"}

        # Get execution levels
        execution_levels = dag.topological_order()

        results: dict[str, Any] = {"status": "completed", "levels": []}
        completed_tasks: set[str] = set()

        for level in execution_levels:
            level_results = []
            for task_id in level:
                task = task_map.get(task_id)
                if not task:
                    continue

                # Build context from completed dependencies
                context_data: dict[str, str] = {}
                for dep_id in (task.dependencies or []):
                    if dep_id in completed_tasks and dep_id in task_map:
                        dep_task = task_map[dep_id]
                        if dep_task.final_output:
                            context_data[dep_id] = dep_task.final_output

                # Execute task
                await group_ws_hub.broadcast(group_id, {
                    "type": "dag_level_start",
                    "data": {"task_id": task_id, "level": len(results["levels"]) + 1},
                })

                lease = None
                try:
                    lease = await self._claim_or_takeover(task.id)
                    if lease is None:
                        level_results.append({"task_id": task_id, "status": "skipped"})
                        continue
                    dag_runner = asyncio.current_task()
                    if dag_runner is not None:
                        self._running_tasks[task_id] = dag_runner
                    heartbeat = asyncio.create_task(self._heartbeat_loop(lease))
                    try:
                        completed = await self._run_single_task_in_dag(task, group, context_data, lease=lease)
                    finally:
                        heartbeat.cancel()
                        try:
                            await heartbeat
                        except asyncio.CancelledError:
                            pass
                        if self._running_tasks.get(task_id) is dag_runner:
                            self._running_tasks.pop(task_id, None)
                    if completed:
                        completed_tasks.add(task_id)
                        level_results.append({"task_id": task_id, "status": "completed"})
                    else:
                        level_results.append({"task_id": task_id, "status": "skipped"})
                except Exception as e:
                    logger.error("dag_task_failed", task_id=task_id, error=str(e))
                    if lease is not None:
                        await self._fail_running_task(task_id, lease.token)
                    level_results.append({"task_id": task_id, "status": "failed", "error": str(e)})

            results["levels"].append(level_results)

        return results

    async def _run_single_task_in_dag(
        self,
        task: AgentGroupTask,
        group: AgentGroup,
        context_data: dict[str, str],
        lease: TaskLease | None = None,
    ) -> bool:
        """Execute a single task within a DAG context."""
        if lease is None:
            lease = await self._claim_or_takeover(task.id)
            if lease is None:
                logger.info("dag_task_not_claimed", task_id=task.id)
                return False
        async with async_session() as db:
            claimed_task = await db.get(AgentGroupTask, task.id)
            if claimed_task is None or claimed_task.status != "running":
                return False
            task = claimed_task

        # Select worker
        worker = None
        if task.worker_id:
            async with async_session() as db:
                worker = (await db.execute(
                    select(AgentGroupMember).where(AgentGroupMember.id == task.worker_id)
                )).scalar_one_or_none()

        if not worker:
            async with async_session() as db:
                worker = (await db.execute(
                    select(AgentGroupMember)
                    .where(AgentGroupMember.group_id == task.group_id)
                    .where(AgentGroupMember.role.in_(["worker", "participant"]))
                )).scalars().first()

        if not worker:
            raise Exception("No worker available")

        # Build full context
        memory_context = await self._inject_memory(task.group_id, task.id, task.description)
        context_parts = [memory_context]
        if context_data:
            ctx_str = "\n\n".join(f"[Task {k} output]:\n{v}" for k, v in context_data.items())
            context_parts.insert(0, ctx_str)

        # Execute worker
        worker_output, worker_tokens = await self._run_agent_with_retry(
            agent_id=worker.agent_id,
            provider=worker.model_provider or "openai",
            model_id=worker.model_id or "gpt-4o",
            api_key=_resolve_api_key(worker.model_provider, worker.api_key_encrypted),
            system_prompt=self._build_worker_prompt(task.description),
            user_message=task.description + "\n\nContext:\n" + "\n".join(context_parts),
            tools=worker.tools or [],
            group_id=task.group_id,
            role="worker",
            base_url=_resolve_base_url(worker.model_provider, None),
        )

        # Reviewer (if any)
        final_output = worker_output
        reviewers = []
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                reviewers = (await db.execute(
                    select(AgentGroupMember)
                    .where(AgentGroupMember.id.in_(t.reviewer_ids or []))
                )).scalars().all()

        if reviewers:
            review_output, _ = await self._run_agent_simple(
                agent_id=reviewers[0].agent_id,
                provider=reviewers[0].model_provider or "openai",
                model_id=reviewers[0].model_id or "gpt-4o",
                api_key=_resolve_api_key(reviewers[0].model_provider, reviewers[0].api_key_encrypted),
                system_prompt=self._build_reviewer_prompt(task.description),
                user_message=f"Review this output:\n{worker_output}",
                tools=reviewers[0].tools or [],
                group_id=task.group_id,
                role="reviewer",
                base_url=_resolve_base_url(reviewers[0].model_provider, None),
            )
            lower = review_output.lower()
            passed = any(k in lower for k in ["通过", "pass", "approved", "acceptable", "valid"])
            final_output = review_output if passed else worker_output

        # Persist result
        if not await self._complete_running_task(
            task.id,
            lease.token,
            status="completed",
            final_output=final_output,
            total_tokens=AgentGroupTask.total_tokens + worker_tokens,
        ):
            logger.info("task_completion_skipped", task_id=task.id)
            return False

        await self._store_memory(task.group_id, task.id, worker.agent_id, final_output, "task_result")
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed",
            "data": {"task_id": task.id, "output": final_output},
        })
        return True

    async def handoff_task(self, task_id: str, target_agent_id: str, reason: str = "") -> dict[str, Any]:
        """Hand off a task from one agent to another.

        """
        async with async_session() as db:
            task = await db.get(AgentGroupTask, task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            target = (
                await db.execute(
                    select(AgentGroupMember).where(AgentGroupMember.agent_id == target_agent_id)
                )
            ).scalar_one_or_none()
            if not target:
                raise HTTPException(status_code=404, detail="Target agent not found")

            # Update task worker
            task.worker_id = target.id
            await db.commit()

            msg = HandoffMessage(
                source_agent=task.worker_id or "",
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

    async def _run_sequential_process(
        self,
        task: AgentGroupTask,
        worker: AgentGroupMember,
        reviewers: list[AgentGroupMember],
        group: AgentGroup,
        lease: TaskLease | None = None,
    ) -> None:
        """Sequential execution: each task gets context from previous tasks in the chain."""
        effective_lease = lease or await self._claim_or_takeover(task.id)
        if effective_lease is None:
            logger.info("sequential_task_not_claimed", task_id=task.id)
            return
        lease = effective_lease
        # Build context from dependent tasks
        context_data = await self._build_context_from_dependencies(task)

        # Inject memory
        memory_context = await self._inject_memory(task.group_id, task.id, task.description)
        full_context = self._merge_context(context_data, memory_context)

        max_rounds = task.max_rounds or 5
        current_round = task.current_round or 0
        worker_output = task.final_output or ""
        all_issues: list[dict[str, Any]] = []

        async def _wait_while_paused(t: AgentGroupTask) -> bool:
            while t.status == "paused":
                await group_ws_hub.broadcast(task.group_id, {
                    "type": "task_update",
                    "data": {"id": t.id, "status": "paused"},
                })
                await asyncio.sleep(1)
                async with async_session() as db:
                    t = await db.get(AgentGroupTask, task.id)
                    if t is None or t.status in ("stopped", "cancelled", "failed", "completed", "partial"):
                        return False
            return True

        async def _checkpoint_and_broadcast(t: AgentGroupTask, round_num: int, output: str, issues: list[dict[str, Any]]) -> None:
            saved = await self._save_checkpoint(task.id, task.group_id, round_num, max_rounds, output, issues, token=lease.token)
            if not saved:
                return
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_checkpoint",
                "data": {"task_id": task.id, "round": round_num},
            })

        try:
            while current_round < max_rounds:
                async with async_session() as db:
                    t = await db.get(AgentGroupTask, task.id)
                    if t is None:
                        logger.error("task_disappeared", task_id=task.id)
                        return
                    if t.status in ("stopped", "cancelled", "failed", "completed", "partial"):
                        return
                    if t.status == "paused":
                        if not await _wait_while_paused(t):
                            return
                    task = t

                current_round += 1

                if not await self._update_progress(task.id, lease.token, current_round=current_round):
                    logger.info("task_progress_skipped", task_id=task.id)
                    return
                async with async_session() as db:
                    current_task = await db.get(AgentGroupTask, task.id)
                    if current_task is None:
                        return
                    task = current_task

                await group_ws_hub.broadcast(task.group_id, {
                    "type": "progress_update",
                    "data": {
                        "current_round": current_round,
                        "max_rounds": max_rounds,
                        "status": "running",
                        "active_member": worker.agent_id,
                    },
                })

                await group_ws_hub.broadcast(task.group_id, {
                    "type": "worker_start",
                    "data": {"member_id": worker.id, "member_name": worker.agent_id, "round": current_round},
                })

                user_message = (
                    self._build_sequential_prompt(task.description, full_context, worker_output, all_issues)
                    if current_round > 1
                    else self._build_initial_prompt(task.description, full_context)
                )

                worker_output = ""
                worker_tokens = 0
                try:
                    worker_output, worker_tokens = await self._run_agent_with_retry(
                        agent_id=worker.agent_id,
                        provider=worker.model_provider or "openai",
                        model_id=worker.model_id or "gpt-4o",
                        api_key=_resolve_api_key(worker.model_provider, worker.api_key_encrypted),
                        system_prompt=self._build_worker_prompt(task.description),
                        user_message=user_message,
                        tools=worker.tools or [],
                        group_id=task.group_id,
                        role="worker",
                        base_url=_resolve_base_url(worker.model_provider, None),
                    )
                    if not worker_output:
                        raise Exception("worker returned empty output after retry")
                except Exception as e:
                    logger.error("worker_failed", task_id=task.id, round=current_round, error=str(e))
                    if not await self._complete_running_task(task.id, lease.token, status="failed"):
                        logger.info("task_failure_skipped", task_id=task.id)
                        return
                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "task_failed",
                        "data": {"task_id": task.id, "error": f"Worker failed after retry: {e}"},
                    })
                    return

                if not await self._task_is_running(task.id, lease.token):
                    logger.info("task_post_worker_skipped", task_id=task.id)
                    return

                await group_ws_hub.broadcast(task.group_id, {
                    "type": "worker_done",
                    "data": {
                        "member_id": worker.id,
                        "member_name": worker.agent_id,
                        "content": worker_output,
                        "tokens_used": worker_tokens,
                    },
                })

                # Step callback
                await self._invoke_step_callback(task, "worker", worker.agent_id, worker_output)

                # Run guardrails
                guardrail_passed, guardrail_feedback = await self._run_guardrails(task, worker_output)
                if not guardrail_passed:
                    all_issues = guardrail_feedback
                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "guardrail_retry",
                        "data": {"round": current_round, "feedback": guardrail_feedback},
                    })
                    continue

                # Human-in-the-loop review
                if task.human_review_required:
                    approved = await self._wait_for_human_review(task, worker_output, lease.token)
                    if not approved:
                        all_issues = [{"description": "Human review rejected or timed out", "severity": "high"}]
                        await group_ws_hub.broadcast(task.group_id, {
                            "type": "human_review_rejected",
                            "data": {"round": current_round},
                        })
                        continue
                    if not await self._task_is_running(task.id, lease.token):
                        return

                # Reviewer turn
                all_issues = []
                for reviewer in reviewers:
                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "reviewer_start",
                        "data": {"member_id": reviewer.id, "member_name": reviewer.agent_id},
                    })

                    review_output = ""
                    review_tokens = 0
                    review_error = None
                    try:
                        async with asyncio.timeout(TASK_TIMEOUT):
                            review_output, _ = await self._run_agent_simple(
                                agent_id=reviewer.agent_id,
                                provider=reviewer.model_provider or "openai",
                                model_id=reviewer.model_id or "gpt-4o",
                                api_key=_resolve_api_key(reviewer.model_provider, reviewer.api_key_encrypted),
                                base_url=_resolve_base_url(reviewer.model_provider, None),
                                system_prompt=self._build_reviewer_prompt(task.description),
                                user_message=self._build_review_prompt(task.description, worker_output),
                                tools=reviewer.tools or [],
                            )
                    except TimeoutError:
                        review_error = f"timeout after {TASK_TIMEOUT}s"
                    except Exception as e:
                        review_error = str(e)

                    if review_error:
                        await group_ws_hub.broadcast(task.group_id, {
                            "type": "reviewer_error",
                            "data": {"member_id": reviewer.id, "member_name": reviewer.agent_id, "error": review_error},
                        })
                        continue

                    lower_output = review_output.lower()
                    passed = any(k in lower_output for k in ["通过", "pass", "approved", "looks good", "accept"])
                    issues = self._parse_issues(review_output)

                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "reviewer_done",
                        "data": {
                            "member_id": reviewer.id,
                            "member_name": reviewer.agent_id,
                            "passed": passed,
                            "issues": issues,
                            "content": review_output,
                            "tokens_used": review_tokens,
                        },
                    })

                    if not passed:
                        all_issues.extend(issues)

                if not all_issues:
                    # Validate structured output if schema provided
                    if task.output_schema:
                        valid, parsed = self._validate_structured_output(worker_output, task.output_schema)
                        if not valid:
                            all_issues = [{"description": "Structured output validation failed", "severity": "high", "details": parsed}]
                            await group_ws_hub.broadcast(task.group_id, {
                                "type": "guardrail_failed",
                                "data": {"reason": "structured_output_validation_failed", "details": parsed},
                            })
                            continue

                    completion_values: dict[str, Any] = {
                        "final_output": worker_output,
                    }
                    if task.output_schema:
                        completion_values["structured_output"] = parsed if 'parsed' in dir() else {}
                    await _checkpoint_and_broadcast(task, current_round, worker_output, [])
                    if not await self._complete_running_task(
                        task.id,
                        lease.token,
                        status="completed",
                        **completion_values,
                    ):
                        logger.info("task_completion_skipped", task_id=task.id)
                        return
                    async with async_session() as db:
                        task = await db.get(AgentGroupTask, task.id)
                        if task is None:
                            return

                    await self._store_memory(task.group_id, task.id, worker.agent_id, worker_output, "task_result")
                    await self._invoke_task_callback(task, worker_output)
                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "task_completed",
                        "data": {"task_id": task.id, "final_output": worker_output, "rounds": current_round},
                    })
                    return

                # Continue to next round for revision
                await _checkpoint_and_broadcast(task, current_round, worker_output, all_issues)

            if not await self._complete_running_task(
                task.id,
                lease.token,
                status="partial",
                final_output=worker_output,
            ):
                logger.info("task_partial_skipped", task_id=task.id)
                return
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_partial",
                "data": {"task_id": task.id, "final_output": worker_output, "rounds": current_round},
            })

        except Exception as e:
            logger.exception("group_task_failed", task_id=task.id)
            try:
                if not await self._complete_running_task(task.id, lease.token, status="failed"):
                    return
            except Exception:
                logger.debug("core.group_collaboration.suppressed", exc_info=True)
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_failed",
                "data": {"task_id": task.id, "error": str(e)},
            })

    async def _run_hierarchical_process(self, task: AgentGroupTask, group: AgentGroup, lease: TaskLease | None = None) -> None:
        """Hierarchical execution: manager agent delegates and validates."""
        effective_lease = lease or await self._claim_or_takeover(task.id)
        if effective_lease is None:
            logger.info("hierarchical_task_not_claimed", task_id=task.id)
            return
        lease = effective_lease
        # Find manager member
        manager_member = None
        if group.manager_agent_id:
            async with async_session() as db:
                manager_member = (
                    await db.execute(
                        select(AgentGroupMember).where(
                            AgentGroupMember.id == group.manager_agent_id,
                            AgentGroupMember.group_id == group.id,
                        )
                    )
                ).scalar_one_or_none()

        if not manager_member:
            # Fallback: pick first member with manager/coordinator role, or first worker
            async with async_session() as db:
                candidates = (
                    await db.execute(
                        select(AgentGroupMember).where(
                            AgentGroupMember.group_id == group.id,
                            AgentGroupMember.role.in_(["manager", "coordinator", "worker"]),
                        )
                    )
                ).scalars().all()
                if candidates:
                    manager_member = candidates[0]

        if not manager_member:
            logger.error("no_manager_found", group_id=group.id)
            await self._fail_running_task(task.id, lease.token)
            return

        workers = [
            m for m in group.members
            if m.id != manager_member.id and m.role in ("worker", "participant")
        ]
        if not workers:
            logger.error("no_workers_found", group_id=group.id)
            await self._fail_running_task(task.id, lease.token)
            return

        await group_ws_hub.broadcast(task.group_id, {
            "type": "manager_start",
            "data": {"member_id": manager_member.id, "member_name": manager_member.agent_id},
        })

        # Manager plans subtasks
        subtask_prompt = self._build_manager_planning_prompt(task.description, workers)
        manager_plan = ""
        manager_tokens = 0
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                manager_plan, manager_tokens = await self._run_agent_simple(
                    agent_id=manager_member.agent_id,
                    provider=manager_member.model_provider or "openai",
                    model_id=manager_member.model_id or "gpt-4o",
                    api_key=_resolve_api_key(manager_member.model_provider, manager_member.api_key_encrypted),
                    base_url=_resolve_base_url(manager_member.model_provider, None),
                    system_prompt=self._build_manager_prompt(task.description),
                    user_message=subtask_prompt,
                    tools=manager_member.tools or [],
                )
        except Exception as e:
            logger.error("manager_failed", task_id=task.id, error=str(e))
            if await self._fail_running_task(task.id, lease.token):
                await group_ws_hub.broadcast(task.group_id, {
                    "type": "task_failed",
                    "data": {"task_id": task.id, "error": f"Manager planning failed: {e}"},
                })
            return

        if not await self._task_is_running(task.id, lease.token):
            return

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_plan",
            "data": {"content": manager_plan, "tokens_used": manager_tokens},
        })

        # Delegate subtasks to workers (simple round-robin for now)
        subtask_outputs: dict[str, str] = {}
        for i, worker in enumerate(workers):
            if not await self._task_is_running(task.id, lease.token):
                return
            subtask_desc = f"{task.description}\n\nContext from manager: {manager_plan}\n"
            if i > 0 and subtask_outputs:
                previous = list(subtask_outputs.values())[-1]
                subtask_desc += f"\nPrevious subtask output: {previous}\n"

            await group_ws_hub.broadcast(task.group_id, {
                "type": "hierarchical_delegate",
                "data": {"worker_id": worker.id, "worker_name": worker.agent_id, "subtask_index": i + 1},
            })

            worker_output, worker_tokens = await self._run_agent_with_retry(
                agent_id=worker.agent_id,
                provider=worker.model_provider or "openai",
                model_id=worker.model_id or "gpt-4o",
                api_key=decrypt_api_key(worker.api_key_encrypted or ""),
                system_prompt=self._build_worker_prompt(subtask_desc),
                user_message=subtask_desc,
                tools=worker.tools or [],
                group_id=task.group_id,
                role="worker",
            )
            if not await self._task_is_running(task.id, lease.token):
                return
            subtask_outputs[worker.id] = worker_output

            await self._invoke_step_callback(task, "worker", worker.agent_id, worker_output)

            await group_ws_hub.broadcast(task.group_id, {
                "type": "hierarchical_delegate_done",
                "data": {"worker_id": worker.id, "worker_name": worker.agent_id, "subtask_index": i + 1, "tokens_used": worker_tokens},
            })

        # Manager validates
        validation_prompt = self._build_manager_validation_prompt(task.description, manager_plan, subtask_outputs)
        manager_validation = ""
        manager_validation_tokens = 0
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                manager_validation, manager_validation_tokens = await self._run_agent_simple(
                    agent_id=manager_member.agent_id,
                    provider=manager_member.model_provider or "openai",
                    model_id=manager_member.model_id or "gpt-4o",
                    api_key=_resolve_api_key(manager_member.model_provider, manager_member.api_key_encrypted),
                    base_url=_resolve_base_url(manager_member.model_provider, None),
                    system_prompt=self._build_manager_prompt(task.description),
                    user_message=validation_prompt,
                    tools=manager_member.tools or [],
                )
        except Exception as e:
            logger.error("manager_validation_failed", task_id=task.id, error=str(e))
            manager_validation = f"Validation error: {e}"

        if not await self._task_is_running(task.id, lease.token):
            return

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_validate",
            "data": {"content": manager_validation, "tokens_used": manager_validation_tokens},
        })

        # Check if validation passed
        lower_validation = manager_validation.lower()
        passed = any(k in lower_validation for k in ["通过", "pass", "approved", "acceptable", "valid"])

        final_output = manager_validation if passed else "\n\n".join(subtask_outputs.values())

        async with async_session() as db:
            completion = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task.id)
                .where(AgentGroupTask.status == "running")
                .where(AgentGroupTask.lease_token == lease.token)
                .values(
                    status="completed" if passed else "partial",
                    final_output=final_output,
                    lease_owner=None,
                    lease_expires_at=None,
                    completed_at=datetime.now(UTC),
                )
            )
            if completion.rowcount != 1:
                await db.rollback()
                logger.info("task_completion_skipped", task_id=task.id)
                return
            await db.commit()

        await self._store_memory(task.group_id, task.id, manager_member.agent_id, final_output, "task_result")
        await self._invoke_task_callback(task, final_output)

        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed" if passed else "task_partial",
            "data": {"task_id": task.id, "final_output": final_output, "manager_validation": manager_validation},
        })

    async def _run_group_chat_process(self, task: AgentGroupTask, group: AgentGroup, lease: TaskLease | None = None) -> None:
        """Group chat process: agents discuss in rounds until consensus."""
        effective_lease = lease or await self._claim_or_takeover(task.id)
        if effective_lease is None:
            logger.info("group_chat_task_not_claimed", task_id=task.id)
            return
        lease = effective_lease
        participants = [m for m in group.members if m.role in ("worker", "participant", "reviewer")]
        if not participants:
            participants = group.members[:]

        max_rounds = task.max_rounds or 5
        conversation: list[dict[str, Any]] = []
        consensus_reached = False

        for round_num in range(1, max_rounds + 1):
            async with async_session() as db:
                t = await db.get(AgentGroupTask, task.id)
                if t is None or t.status in ("stopped", "cancelled", "failed", "completed", "partial"):
                    return
                if t and t.status == "paused":
                    while t.status == "paused":
                        await asyncio.sleep(1)
                        t = await db.get(AgentGroupTask, task.id)
                        if not t or t.status in ("stopped", "cancelled", "failed", "completed", "partial"):
                            return

            await group_ws_hub.broadcast(task.group_id, {
                "type": "progress_update",
                "data": {"current_round": round_num, "max_rounds": max_rounds, "status": "running"},
            })

            remaining_participants = list(participants)
            while remaining_participants:
                participant = await self._select_group_chat_speaker(
                    group,
                    task_description=task.description,
                    candidates=remaining_participants,
                    conversation=conversation,
                )
                remaining_participants.remove(participant)
                if not await self._task_is_running(task.id, lease.token):
                    return
                await group_ws_hub.broadcast(task.group_id, {
                    "type": "group_chat_turn",
                    "data": {
                        "member_id": participant.id,
                        "member_name": participant.agent_id,
                        "round": round_num,
                        "selection_method": "auto" if group.manager_llm else "round_robin",
                    },
                })

                # Build conversation context
                context_messages = self._build_group_chat_context(task.description, conversation)

                output = ""
                participant_tokens = 0
                try:
                    async with asyncio.timeout(TASK_TIMEOUT):
                        output, participant_tokens = await self._run_agent_simple(
                            agent_id=participant.agent_id,
                            provider=participant.model_provider or "openai",
                            model_id=participant.model_id or "gpt-4o",
                            api_key=_resolve_api_key(participant.model_provider, participant.api_key_encrypted),
                            base_url=_resolve_base_url(participant.model_provider, None),
                            system_prompt=self._build_group_chat_prompt(participant.role),
                            user_message=context_messages,
                            tools=participant.tools or [],
                        )
                except Exception as e:
                    logger.error("group_chat_agent_failed", agent_id=participant.agent_id, error=str(e))
                    output = f"[Error: {e}]"

                if not await self._task_is_running(task.id, lease.token):
                    return

                conversation.append({
                    "round": round_num,
                    "agent_id": participant.agent_id,
                    "agent_name": participant.agent_id,
                    "role": participant.role,
                    "content": output,
                })

                await group_ws_hub.broadcast(task.group_id, {
                    "type": "message",
                    "data": {
                        "sender_id": participant.agent_id,
                        "sender_name": participant.agent_id,
                        "content": output,
                        "message_type": "text",
                        "round": round_num,
                        "tokens_used": participant_tokens,
                    },
                })

                await self._invoke_step_callback(task, participant.role, participant.agent_id, output)

            # Check for consensus (simple heuristic: last N messages contain agreement keywords)
            if round_num >= 2:
                recent = conversation[-(len(participants)):]
                agreement_count = sum(
                    1 for m in recent
                    if any(k in m["content"].lower() for k in ["同意", "agree", "consensus", "好的", "approved", "accept", "looks good"])
                )
                if agreement_count >= len(participants) * 0.6:
                    consensus_reached = True
                    break

        # Summarize
        final_output = self._summarize_group_chat(task.description, conversation)
        if not await self._complete_running_task(
            task.id,
            lease.token,
            status="completed" if consensus_reached else "partial",
            final_output=final_output,
        ):
            logger.info("task_completion_skipped", task_id=task.id)
            return

        await self._store_memory(task.group_id, task.id, "group_chat", final_output, "task_result")
        await self._invoke_task_callback(task, final_output)

        await group_ws_hub.broadcast(task.group_id, {
            "type": "group_chat_consensus",
            "data": {"reached": consensus_reached, "final_output": final_output},
        })
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed" if consensus_reached else "task_partial",
            "data": {"task_id": task.id, "final_output": final_output, "rounds": round_num},
        })

    async def _build_context_from_dependencies(self, task: AgentGroupTask) -> dict[str, Any]:
        """Build context from tasks listed in the `context` field."""
        context_data: dict[str, Any] = {}
        if not task.context:
            return context_data
        async with async_session() as db:
            for dep_task_id in task.context:
                dep_task = await db.get(AgentGroupTask, dep_task_id)
                if dep_task and dep_task.final_output:
                    context_data[dep_task_id] = {
                        "description": dep_task.description,
                        "output": dep_task.final_output,
                        "status": dep_task.status,
                        "completed_at": dep_task.completed_at.isoformat() if dep_task.completed_at else None,
                    }
        return context_data

    async def _inject_memory(self, group_id: str, task_id: str, query: str) -> str:
        """Retrieve relevant memories and format them for prompt injection."""
        async with async_session() as db:
            memories = (
                await db.execute(
                    select(AgentGroupMemory).where(
                        AgentGroupMemory.group_id == group_id,
                        AgentGroupMemory.memory_type.in_(["short_term", "long_term"]),
                    ).order_by(AgentGroupMemory.importance.desc(), AgentGroupMemory.created_at.desc()).limit(10)
                )
            ).scalars().all()

        if not memories:
            return ""

        memory_lines = ["Relevant memories:"]
        for mem in memories:
            memory_lines.append(f"- [{mem.memory_type}] {mem.content}")

        await group_ws_hub.broadcast(group_id, {
            "type": "memory_injected",
            "data": {"task_id": task_id, "count": len(memories)},
        })

        return "\n".join(memory_lines)

    async def _store_memory(self, group_id: str, task_id: str, agent_id: str, content: str, memory_type: str = "task_result") -> None:
        """Store a memory entry for future retrieval."""
        summary = content[:200] + "..." if len(content) > 200 else content
        memory = AgentGroupMemory(
            group_id=group_id,
            task_id=task_id,
            source_agent_id=agent_id,
            content=content,
            summary=summary,
            memory_type="long_term",
            memory_category=memory_type,
            importance=0.7,
            tags=["task_output"],
        )
        async with async_session() as db:
            db.add(memory)
            await db.commit()

        await group_ws_hub.broadcast(group_id, {
            "type": "memory_stored",
            "data": {"task_id": task_id, "memory_type": memory_type},
        })

    async def _run_guardrails(self, task: AgentGroupTask, output: str) -> tuple[bool, list[dict[str, Any]]]:
        """Run guardrails on task output. Returns (passed, feedback_issues)."""
        if not task.guardrails:
            return True, []

        issues: list[dict[str, Any]] = []
        for guardrail in task.guardrails:
            g_type = guardrail.get("type", "llm")
            if g_type == "llm":
                passed, feedback = await self._run_llm_guardrail(task, output, guardrail)
                if not passed:
                    issues.extend(feedback)
            elif g_type == "function":
                passed, feedback = await self._run_function_guardrail(output, guardrail)
                if not passed:
                    issues.extend(feedback)
            elif g_type == "schema" and task.output_schema:
                passed, errors = self._validate_structured_output(output, task.output_schema)
                if not passed:
                    issues.append({"description": "Schema validation failed", "severity": "high", "details": errors})

        await group_ws_hub.broadcast(task.group_id, {
            "type": "guardrail_check",
            "data": {"passed": len(issues) == 0, "issues_count": len(issues)},
        })

        return len(issues) == 0, issues

    async def _run_llm_guardrail(self, task: AgentGroupTask, output: str, guardrail: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
        """Run an LLM-based guardrail check."""
        prompt = guardrail.get("validation_prompt") or f"""Review the following output against these requirements:
{guardrail.get('description', '')}

Output:
{output}

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""

        review_output = ""
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                review_output, _ = await self._run_agent_simple(
                    agent_id="guardrail-validator",
                    provider="openai",
                    model_id="gpt-4o",
                    api_key=_resolve_api_key("openai", ""),
                    base_url=_resolve_base_url("openai", None),
                    system_prompt="You are a strict quality validator.",
                    user_message=prompt,
                    tools=[],
                )
        except Exception as e:
            logger.error("llm_guardrail_failed", task_id=task.id, error=str(e))
            return True, []

        lower_output = review_output.lower()
        passed = any(k in lower_output for k in ["通过", "pass", "approved", "looks good", "accept"])
        issues = self._parse_issues(review_output) if not passed else []

        await group_ws_hub.broadcast(task.group_id, {
            "type": "guardrail_passed" if passed else "guardrail_failed",
            "data": {"guardrail_name": guardrail.get("name", "unnamed"), "passed": passed},
        })

        return passed, issues

    async def _run_function_guardrail(self, output: str, guardrail: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
        """Run a function-based guardrail."""
        func_path = guardrail.get("validation_function")
        if not func_path:
            return True, []

        try:
            module_path, func_name = func_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            fn = getattr(module, func_name)
            result = fn(output)
            if asyncio.iscoroutinefunction(fn):
                result = await result
            if isinstance(result, bool):
                return result, []
            if isinstance(result, tuple):
                return result
            return True, []
        except Exception as e:
            logger.error("function_guardrail_failed", func_path=func_path, error=str(e))
            return True, []

    def _validate_structured_output(self, output: str, schema: dict[str, Any]) -> tuple[bool, Any]:
        """Validate output against JSON schema."""
        from app.core.json_schema import validate_structured_output
        valid, parsed, errors = validate_structured_output(output, schema)
        if not valid:
            return False, {"errors": errors[:10], "raw": output[:500]}
        return True, parsed

    async def _save_checkpoint(self, task_id: str, group_id: str, current_round: int, max_rounds: int, current_artifact: str, all_issues: list[dict[str, Any]], token: int | None = None) -> bool:
        """Save execution checkpoint for resume capability, fenced by lease token."""
        async with async_session() as db:
            if token is not None:
                guard = await db.execute(
                    update(AgentGroupTask)
                    .where(AgentGroupTask.id == task_id)
                    .where(AgentGroupTask.status == "running")
                    .where(AgentGroupTask.lease_owner == self.instance_id)
                    .where(AgentGroupTask.lease_token == token)
                    .where(AgentGroupTask.lease_expires_at >= _db_now())
                    .values(lease_token=AgentGroupTask.lease_token)
                )
                if guard.rowcount != 1:
                    await db.rollback()
                    logger.info("checkpoint_save_skipped", task_id=task_id)
                    return False
            stmt = select(AgentGroupTask.description, AgentGroupTask.output_schema).where(
                AgentGroupTask.id == task_id,
                AgentGroupTask.status == "running",
            )
            if token is not None:
                stmt = stmt.where(AgentGroupTask.lease_token == token)
            row = (await db.execute(stmt)).one_or_none()
            if row is None:
                logger.info("checkpoint_save_skipped", task_id=task_id)
                return False
            checkpoint = AgentGroupTaskCheckpoint(
                group_id=group_id,
                task_id=task_id,
                status="running",
                current_round=current_round,
                max_rounds=max_rounds,
                current_artifact=current_artifact,
                all_issues=all_issues,
                task_description=row.description,
                output_schema=row.output_schema,
            )
            db.add(checkpoint)
            await db.commit()
        return True

    async def _load_latest_checkpoint(self, task_id: str) -> AgentGroupTaskCheckpoint | None:
        """Load the latest checkpoint for a task."""
        async with async_session() as db:
            return (
                await db.execute(
                    select(AgentGroupTaskCheckpoint).where(
                        AgentGroupTaskCheckpoint.task_id == task_id
                    ).order_by(AgentGroupTaskCheckpoint.created_at.desc()).limit(1)
                )
            ).scalar_one_or_none()

    async def _resume_from_checkpoint(
        self,
        task: AgentGroupTask,
        checkpoint: AgentGroupTaskCheckpoint,
        token: int | None = None,
    ) -> AgentGroupTask | None:
        """Resume task execution from a checkpoint."""
        restored_task = None
        async with async_session() as db:
            stmt = (
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task.id)
                .where(AgentGroupTask.status.in_(("running", "paused")))
                .values(
                    status="running",
                    final_output=checkpoint.current_artifact,
                    current_round=checkpoint.current_round,
                )
            )
            if token is not None:
                stmt = stmt.where(AgentGroupTask.lease_token == token)
            restore = await db.execute(stmt)
            if restore.rowcount != 1:
                await db.rollback()
                return None
            await db.commit()
            restored_task = await db.get(AgentGroupTask, task.id)
        if restored_task is None:
            return None
        await group_ws_hub.broadcast(task.group_id, {
            "type": "checkpoint_restored",
            "data": {"task_id": task.id, "checkpoint_id": checkpoint.id, "round": checkpoint.current_round},
        })
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_partial",
            "data": {"task_id": task.id, "final_output": checkpoint.current_artifact, "rounds": checkpoint.current_round},
        })
        return restored_task

    # ─── Task Cancellation ────────────────────────────────────────────────

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task by its ID."""
        task = self._running_tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        return True

    async def cancel_and_wait(self, task_id: str) -> bool:
        """Cancel a local executor and wait until it releases its task slot."""
        task = self._running_tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True

    # ─── Review State Machine ────────────────────────────────────────────

    def get_review_state(self, task_id: str, reviewer_id: str) -> str:
        """Get the review state for a reviewer on a task. Defaults to 'pending'."""
        return self._review_states.get(task_id, {}).get(reviewer_id, "pending")

    def set_review_state(self, task_id: str, reviewer_id: str, state: str) -> None:
        """Set the review state for a reviewer on a task."""
        if task_id not in self._review_states:
            self._review_states[task_id] = {}
        self._review_states[task_id][reviewer_id] = state

    def get_task_review_summary(self, task_id: str) -> dict[str, int]:
        """Get a summary of review states for a task."""
        states = self._review_states.get(task_id, {})
        summary: dict[str, int] = {"pending": 0, "approved": 0, "rejected": 0}
        for s in states.values():
            summary[s] = summary.get(s, 0) + 1
        return summary

    async def _invoke_step_callback(self, task: AgentGroupTask, role: str, agent_id: str, output: str) -> None:
        """Invoke step callback if configured."""
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

    async def _invoke_task_callback(self, task: AgentGroupTask, final_output: str) -> None:
        """Invoke task callback if configured."""
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

    async def _wait_for_human_review(self, task: AgentGroupTask, output: str, token: int) -> bool:
        """Wait for human review if required. Returns True if approved, False otherwise."""
        if not task.human_review_required:
            return True

        async with async_session() as db:
            transition = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task.id)
                .where(AgentGroupTask.status == "running")
                .where(AgentGroupTask.lease_token == token)
                .values(status="awaiting_human_review", human_review_status="pending")
            )
            if transition.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()

        await group_ws_hub.broadcast(task.group_id, {
            "type": "human_review_needed",
            "data": {"task_id": task.id, "output": output},
        })

        max_wait = task.human_review_timeout if hasattr(task, 'human_review_timeout') and task.human_review_timeout else 3600
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
                if t.status in ("stopped", "cancelled", "failed"):
                    return False

        async with async_session() as db:
            timeout_transition = await db.execute(
                update(AgentGroupTask)
                .where(AgentGroupTask.id == task.id)
                .where(AgentGroupTask.status == "awaiting_human_review")
                .where(AgentGroupTask.lease_token == token)
                .values(status="running")
            )
            if timeout_transition.rowcount != 1:
                await db.rollback()
                return False
            await db.commit()
        return False

        logger.warning("human_review_timeout", task_id=task.id, waited_seconds=waited)
        return False

    def _merge_context(self, context_data: dict[str, Any], memory_context: str) -> str:
        """Merge task context and memory context into a single string."""
        parts = []
        if context_data:
            parts.append("Context from previous tasks:")
            for task_id, ctx in context_data.items():
                parts.append(f"- Task {task_id}: {ctx.get('output', '')[:500]}")
        if memory_context:
            parts.append(memory_context)
        return "\n\n".join(parts)

    def _build_initial_prompt(self, task_description: str, context: str) -> str:
        parts = [f"Task: {task_description}"]
        if context:
            parts.append(f"\nContext:\n{context}")
        return "\n".join(parts)

    def _build_sequential_prompt(self, task_description: str, context: str, previous_output: str, issues: list[dict[str, Any]]) -> str:
        parts = [f"Task: {task_description}"]
        if context:
            parts.append(f"\nContext from previous tasks and memory:\n{context}")
        parts.append(f"\nPrevious output:\n{previous_output}")
        if issues:
            issue_descriptions = [i.get("description", str(i)) for i in issues]
            parts.append(f"\nIssues to fix:\n{chr(10).join('- ' + desc for desc in issue_descriptions)}")
        return "\n".join(parts)

    def _build_group_chat_context(self, task_description: str, conversation: list[dict[str, Any]]) -> str:
        parts = [f"Task: {task_description}\n"]
        for msg in conversation:
            parts.append(f"[{msg.get('agent_name', 'Unknown')} ({msg.get('role', 'participant')})]: {msg.get('content', '')}")
        return "\n".join(parts)

    async def _select_group_chat_speaker(
        self,
        group: AgentGroup,
        *,
        task_description: str,
        candidates: list[AgentGroupMember],
        conversation: list[dict[str, Any]],
    ) -> AgentGroupMember:
        """Select the next speaker with the manager LLM and deterministic fallback."""
        if not candidates:
            raise ValueError("No speaker candidates")
        if not group.manager_llm or len(candidates) == 1:
            return candidates[0]

        manager_member = next(
            (member for member in group.members if member.agent_id == group.manager_agent_id),
            None,
        )
        model_ref = group.manager_llm.strip()
        if "/" in model_ref:
            provider, model_id = model_ref.split("/", 1)
        else:
            provider = manager_member.model_provider if manager_member and manager_member.model_provider else "openai"
            model_id = model_ref

        candidate_lines = "\n".join(
            f"- {candidate.agent_id} ({candidate.role})" for candidate in candidates
        )
        recent_context = self._build_group_chat_context(task_description, conversation[-12:])
        selector_prompt = f"""Choose the best next speaker for this group discussion.

Candidates:
{candidate_lines}

Conversation:
{recent_context}

Return only JSON in this form: {{"agent_id": "candidate-id"}}"""

        try:
            output, _ = await self._run_agent_simple(
                agent_id=manager_member.agent_id if manager_member and manager_member.agent_id else "group-chat-selector",
                provider=provider,
                model_id=model_id,
                api_key=_resolve_api_key(
                    provider,
                    manager_member.api_key_encrypted if manager_member else None,
                ),
                base_url=_resolve_base_url(provider, None),
                system_prompt=(
                    "You select the next speaker in a multi-agent discussion. "
                    "Choose exactly one provided candidate based on role and conversation context."
                ),
                user_message=selector_prompt,
                tools=[],
            )
            cleaned = output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                selected_id = str(json.loads(cleaned).get("agent_id", ""))
            except (json.JSONDecodeError, AttributeError):
                selected_id = ""
            if selected_id:
                for candidate in candidates:
                    if candidate.agent_id == selected_id:
                        return candidate

            mentioned = [
                candidate for candidate in candidates
                if candidate.agent_id and re.search(
                    rf"(?<![\w-]){re.escape(candidate.agent_id)}(?![\w-])",
                    output,
                )
            ]
            if len(mentioned) == 1:
                return mentioned[0]
        except Exception as e:
            logger.warning("group_chat_speaker_selection_failed", error=str(e))

        return candidates[0]

    def _build_manager_planning_prompt(self, task_description: str, workers: list[AgentGroupMember]) -> str:
        worker_names = [f"- {w.agent_id} ({w.role})" for w in workers]
        return f"""Break down the following task into subtasks for the available workers.

Task: {task_description}

Available workers:
{chr(10).join(worker_names)}

Provide a plan with:
1. Subtask assignments to specific workers
2. Expected output for each subtask
3. Dependencies between subtasks"""

    def _build_manager_validation_prompt(self, task_description: str, plan: str, subtask_outputs: dict[str, str]) -> str:
        outputs_text = "\n\n".join(
            f"Worker {wid} output:\n{output}" for wid, output in subtask_outputs.items()
        )
        return f"""Validate whether the subtask outputs collectively satisfy the original task.

Original task: {task_description}

Manager plan: {plan}

Subtask outputs:
{outputs_text}

Respond with:
1. "通过" if the combined outputs satisfy the task requirements, or "不通过" if not.
2. If not passing, list specific issues or missing requirements."""

    async def _run_agent(self, agent_id: str, provider: str, model_id: str, api_key: str, system_prompt: str, user_message: str, tools: list[str], base_url: str | None = None) -> AsyncIterator[AgentEvent]:
        """Run a single agent turn and yield events."""
        engine = AgentEngine(self.model_registry, self.tool_registry)
        session = engine.create_session(
            agent_id=agent_id,
            user_id="default-user",
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            system_prompt=system_prompt,
            tools=tools,
        )
        async for event in engine.run(session, user_message):
            yield event

    async def _run_agent_simple(self, agent_id: str, provider: str, model_id: str, api_key: str, system_prompt: str, user_message: str, tools: list[str], base_url: str | None = None) -> tuple[str, int]:
        """Run a single agent turn and return (output, tokens_used)."""
        output = ""
        total_tokens = 0
        async for event in self._run_agent(agent_id, provider, model_id, api_key, system_prompt, user_message, tools, base_url):
            if event.type == AgentEventType.TEXT:
                output += event.data.get("content", "")
            elif event.type == AgentEventType.TOOL_CALL:
                pass
            elif event.type == AgentEventType.DONE:
                total_tokens += event.data.get("tokens_used", 0)
                break
            elif event.type == AgentEventType.ERROR:
                raise Exception(event.data.get("error", "unknown_error"))
        return output, total_tokens

    def _get_fallback_model(self, provider: str, model_id: str) -> tuple[str, str] | None:
        """Get fallback model for degradation."""
        key = model_id.lower()
        if key in FALLBACK_MODELS:
            return FALLBACK_MODELS[key]
        from app.models.registry import MODEL_ALIASES
        if key in MODEL_ALIASES:
            _, resolved_model = MODEL_ALIASES[key]
            if resolved_model.lower() in FALLBACK_MODELS:
                return FALLBACK_MODELS[resolved_model.lower()]
        return None

    async def _run_agent_with_retry(self, agent_id: str, provider: str, model_id: str, api_key: str, system_prompt: str, user_message: str, tools: list[str], group_id: str, role: str = "worker", base_url: str | None = None) -> tuple[str, int]:
        """Run agent with retry and fallback, returns (output, tokens_used) or ("", 0) on failure."""
        last_error: Exception | None = None
        total_tokens = 0

        for attempt in range(MAX_RETRIES + 1):
            try:
                output = ""
                async with asyncio.timeout(TASK_TIMEOUT):
                    output, total_tokens = await self._run_agent_simple(
                        agent_id=agent_id,
                        provider=provider,
                        model_id=model_id,
                        api_key=api_key,
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tools=tools,
                        base_url=base_url,
                    )
                if output or not last_error:
                    return output, total_tokens
            except TimeoutError as e:
                last_error = e
            except Exception as e:
                last_error = e

            if attempt < MAX_RETRIES:
                await group_ws_hub.broadcast(group_id, {
                    "type": "system_message",
                    "data": {"content": f"{role} 调用失败，正在重试 ({attempt + 1}/{MAX_RETRIES})..."},
                })

        # Fallback to degraded model
        fallback = self._get_fallback_model(provider, model_id)
        if fallback:
            fb_provider, fb_model = fallback
            await group_ws_hub.broadcast(group_id, {
                "type": "system_message",
                "data": {"content": f"正在降级到 {fb_model}..."},
            })
            try:
                output = ""
                async with asyncio.timeout(TASK_TIMEOUT):
                    output, total_tokens = await self._run_agent_simple(
                        agent_id=agent_id,
                        provider=fb_provider,
                        model_id=fb_model,
                        api_key=api_key,
                        system_prompt=system_prompt,
                        user_message=user_message,
                        tools=tools,
                        base_url=base_url,
                    )
                if output:
                    return output, total_tokens
            except Exception:
                logger.debug("core.group_collaboration.suppressed", exc_info=True)

        logger.error(f"{role}_failed_after_retry", agent_id=agent_id, error=str(last_error) if last_error else "unknown")
        return "", 0

    def _build_worker_prompt(self, task_description: str) -> str:
        role_prompts = {
            "planner": "You are a planner agent. Break down complex tasks into clear, actionable steps.",
            "researcher": "You are a researcher agent. Gather information, analyze sources, and provide well-structured findings.",
            "executor": "You are an executor agent. Complete tasks thoroughly and precisely, delivering high-quality output.",
            "auditor": "You are an auditor agent. Review work carefully, identify issues, and ensure quality standards are met.",
        }
        role_desc = role_prompts.get("executor", role_prompts["executor"])
        return f"""{role_desc}

Task: {task_description}

Produce a complete, high-quality output. Be thorough and precise."""

    def _build_manager_prompt(self, task_description: str) -> str:
        return f"""You are a manager agent responsible for coordinating workers to complete tasks.

Task: {task_description}

Your responsibilities:
1. Break down the task into clear subtasks
2. Assign subtasks to appropriate workers
3. Validate worker outputs
4. Synthesize final results

Be decisive and thorough."""

    def _build_reviewer_prompt(self, task_description: str) -> str:
        return f"""You are a reviewer agent.
Review the following output against the task requirements.

Task: {task_description}
Output: [WORKER_OUTPUT]

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""

    def _build_review_prompt(self, task_description: str, worker_output: str) -> str:
        return f"""Review the following output against the task requirements.

Task: {task_description}
Output: {worker_output}

Respond with:
1. "通过" if the output meets all requirements, or "不通过" if not.
2. If not passing, list specific issues found."""

    def _build_group_chat_prompt(self, role: str) -> str:
        role_descriptions = {
            "worker": "You are a collaborative team member. Contribute constructatively to achieve the group's goal.",
            "reviewer": "You are a critical reviewer. Evaluate proposals and suggest improvements.",
            "manager": "You are a coordinator. Keep discussion focused and drive toward consensus.",
            "participant": "You are a team participant. Share ideas and build on others' contributions.",
        }
        desc = role_descriptions.get(role, role_descriptions["participant"])
        return f"""{desc}

You are participating in a group discussion. Be concise, constructive, and focused on the goal."""

    def _summarize_group_chat(self, task_description: str, conversation: list[dict[str, Any]]) -> str:
        """Summarize group chat into final output."""
        lines = [f"Group discussion for: {task_description}\n"]
        for msg in conversation:
            lines.append(f"[{msg.get('agent_name', 'Unknown')}]: {msg.get('content', '')[:500]}")
        return "\n\n".join(lines)

    def _parse_issues(self, review_output: str) -> list[dict[str, Any]]:
        """Extract issues from reviewer output (simple heuristic)."""
        issues = []
        lines = review_output.splitlines()
        for line in lines:
            line = line.strip()
            if line and any(k in line.lower() for k in ["issue", "问题", "error", "missing", "缺少", "错误", "incorrect"]):
                issues.append({"description": line, "severity": "medium"})
        return issues


_group_collaboration_engine: GroupCollaborationEngine | None = None


def get_group_collaboration_engine() -> GroupCollaborationEngine:
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


# Module-level singleton for direct import
group_collaboration_engine = None


def _get_engine_synchronously() -> GroupCollaborationEngine:
    """Get or create the engine synchronously for import-time access."""
    global group_collaboration_engine
    if group_collaboration_engine is None:
        try:
            model_registry = di_resolve("ModelRegistry")
        except KeyError:
            from app.models.registry import ModelRegistry
            model_registry = ModelRegistry()
        group_collaboration_engine = GroupCollaborationEngine(
            model_registry=model_registry,
            tool_registry=__import__("app.tools", fromlist=["ToolRegistry"]).ToolRegistry(),
        )
    return group_collaboration_engine


# Initialize at module import time
group_collaboration_engine = _get_engine_synchronously()
