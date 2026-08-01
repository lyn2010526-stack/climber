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
import structlog
from datetime import datetime, timezone
from typing import Any, Callable

from app.core import AgentEvent, AgentEventType, ChatResult
from app.core.agent_engine import AgentEngine, AgentSession
from app.core.di import resolve as di_resolve
from app.core.group_ws_hub import group_ws_hub
from app.core.task_dag import TaskDAG, TaskNode, HandoffMessage
from app.storage import async_session
from app.storage.models_groups import AgentGroup, AgentGroupMember, AgentGroupTask, AgentGroupMemory, AgentGroupTaskCheckpoint
from sqlalchemy import select

import os

logger = structlog.get_logger(__name__)

def _resolve_api_key(provider: str, stored_key: str | None) -> str:
    """Resolve API key from member config or environment variable fallback."""
    if stored_key:
        return stored_key
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


def register_callback(name: str, fn: Callable[..., Any]) -> None:
    """Register a named callback for use as step_callback or task_callback."""
    CALLBACK_REGISTRY[name] = fn


class GroupCollaborationEngine:
    """Orchestrates multi-agent collaboration with multiple process types."""

    def __init__(self, model_registry: ModelRegistry, tool_registry: Any) -> None:
        self.model_registry = model_registry
        self.tool_registry = tool_registry

    async def run_task(self, task_id: str) -> None:
        """Execute a group task using the group's configured process type."""
        db_task = None
        db_worker = None
        db_reviewers = []
        db_group = None

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
                db_task = task

                group = (
                    await db.execute(
                        select(AgentGroup).where(AgentGroup.id == task.group_id)
                    )
                ).scalar_one_or_none()
                if group is None:
                    logger.error("group_not_found", group_id=task.group_id)
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
                    task.status = "failed"
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

                task.started_at = datetime.now(timezone.utc)
                task.status = "running"
                await db.commit()

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
            await self._resume_from_checkpoint(task, checkpoint)
            return

        # Dispatch based on process type
        process_type = group.process_type or "sequential"
        try:
            if process_type == "sequential":
                await self._run_sequential_process(task, worker, reviewers, group)
            elif process_type == "hierarchical":
                await self._run_hierarchical_process(task, group)
            elif process_type == "group_chat":
                await self._run_group_chat_process(task, group)
            else:
                logger.error("unknown_process_type", process_type=process_type, task_id=task_id)
                task.status = "failed"
                async with async_session() as db:
                    await db.commit()
        except Exception as e:
            logger.exception("group_task_failed", task_id=task_id)
            try:
                async with async_session() as db:
                    t = await db.get(AgentGroupTask, task_id)
                    if t:
                        t.status = "failed"
                        await db.commit()
            except Exception:
                pass
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_failed",
                "data": {"task_id": task_id, "error": str(e)},
            })

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

                try:
                    await self._run_single_task_in_dag(task, group, context_data)
                    completed_tasks.add(task_id)
                    level_results.append({"task_id": task_id, "status": "completed"})
                except Exception as e:
                    logger.error("dag_task_failed", task_id=task_id, error=str(e))
                    level_results.append({"task_id": task_id, "status": "failed", "error": str(e)})

            results["levels"].append(level_results)

        return results

    async def _run_single_task_in_dag(self, task: AgentGroupTask, group: AgentGroup, context_data: dict[str, str]) -> None:
        """Execute a single task within a DAG context."""
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if not t:
                return
            t.status = "running"
            t.started_at = datetime.now(timezone.utc)
            await db.commit()
            task = t

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
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                t.status = "completed"
                t.final_output = final_output
                t.total_tokens = (t.total_tokens or 0) + worker_tokens
                t.completed_at = datetime.now(timezone.utc)
                await db.commit()

        await self._store_memory(task.group_id, task.id, worker.agent_id, final_output, "task_result")
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed",
            "data": {"task_id": task.id, "output": final_output},
        })

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

    async def _run_sequential_process(self, task: AgentGroupTask, worker: AgentGroupMember, reviewers: list[AgentGroupMember], group: AgentGroup) -> None:
        """Sequential execution: each task gets context from previous tasks in the chain."""
        # Build context from dependent tasks
        context_data = await self._build_context_from_dependencies(task)

        # Inject memory
        memory_context = await self._inject_memory(task.group_id, task.id, task.description)
        full_context = self._merge_context(context_data, memory_context)

        max_rounds = task.max_rounds or 5
        current_round = 0
        worker_output = ""
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
                    if t is None or t.status in ("stopped", "failed", "completed"):
                        return False
            return True

        async def _checkpoint_and_broadcast(t: AgentGroupTask, round_num: int, output: str, issues: list[dict[str, Any]]) -> None:
            await self._save_checkpoint(task.id, task.group_id, round_num, max_rounds, output, issues)
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
                    if t.status == "stopped":
                        return
                    if t.status == "paused":
                        if not await _wait_while_paused(t):
                            return
                    task = t

                current_round += 1

                async with async_session() as db:
                    t = await db.get(AgentGroupTask, task.id)
                    if t:
                        t.current_round = current_round
                        t.status = "running"
                        await db.commit()
                        task = t

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
                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "task_failed",
                        "data": {"task_id": task.id, "error": f"Worker failed after retry: {e}"},
                    })
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
                    approved = await self._wait_for_human_review(task, worker_output)
                    if not approved:
                        all_issues = [{"description": "Human review rejected or timed out", "severity": "high"}]
                        await group_ws_hub.broadcast(task.group_id, {
                            "type": "human_review_rejected",
                            "data": {"round": current_round},
                        })
                        continue

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
                            review_output, review_tokens = await self._run_agent_simple(
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

                    async with async_session() as db:
                        t = await db.get(AgentGroupTask, task.id)
                        if t:
                            t.status = "completed"
                            t.final_output = worker_output
                            if task.output_schema:
                                t.structured_output = parsed if 'parsed' in dir() else {}
                            t.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                            task = t

                    await self._store_memory(task.group_id, task.id, worker.agent_id, worker_output, "task_result")
                    await self._invoke_task_callback(task, worker_output)
                    await _checkpoint_and_broadcast(task, current_round, worker_output, [])

                    await group_ws_hub.broadcast(task.group_id, {
                        "type": "task_completed",
                        "data": {"task_id": task.id, "final_output": worker_output, "rounds": current_round},
                    })
                    return

                # Continue to next round for revision
                await _checkpoint_and_broadcast(task, current_round, worker_output, all_issues)

            async with async_session() as db:
                t = await db.get(AgentGroupTask, task.id)
                if t:
                    t.status = "partial"
                    t.final_output = worker_output
                    t.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_partial",
                "data": {"task_id": task.id, "final_output": worker_output, "rounds": current_round},
            })

        except Exception as e:
            logger.exception("group_task_failed", task_id=task.id)
            try:
                async with async_session() as db:
                    t = await db.get(AgentGroupTask, task.id)
                    if t:
                        t.status = "failed"
                        await db.commit()
            except Exception:
                pass
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_failed",
                "data": {"task_id": task.id, "error": str(e)},
            })

    async def _run_hierarchical_process(self, task: AgentGroupTask, group: AgentGroup) -> None:
        """Hierarchical execution: manager agent delegates and validates."""
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
            return

        workers = [
            m for m in group.members
            if m.id != manager_member.id and m.role in ("worker", "participant")
        ]
        if not workers:
            logger.error("no_workers_found", group_id=group.id)
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
            await group_ws_hub.broadcast(task.group_id, {
                "type": "task_failed",
                "data": {"task_id": task.id, "error": f"Manager planning failed: {e}"},
            })
            return

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_plan",
            "data": {"content": manager_plan, "tokens_used": manager_tokens},
        })

        # Delegate subtasks to workers (simple round-robin for now)
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

            worker_output, worker_tokens = await self._run_agent_with_retry(
                agent_id=worker.agent_id,
                provider=worker.model_provider or "openai",
                model_id=worker.model_id or "gpt-4o",
                api_key=worker.api_key_encrypted or "",
                system_prompt=self._build_worker_prompt(subtask_desc),
                user_message=subtask_desc,
                tools=worker.tools or [],
                group_id=task.group_id,
                role="worker",
            )
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

        await group_ws_hub.broadcast(task.group_id, {
            "type": "hierarchical_validate",
            "data": {"content": manager_validation, "tokens_used": manager_validation_tokens},
        })

        # Check if validation passed
        lower_validation = manager_validation.lower()
        passed = any(k in lower_validation for k in ["通过", "pass", "approved", "acceptable", "valid"])

        final_output = manager_validation if passed else "\n\n".join(subtask_outputs.values())

        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                t.status = "completed" if passed else "partial"
                t.final_output = final_output
                t.completed_at = datetime.now(timezone.utc)
                await db.commit()

        await self._store_memory(task.group_id, task.id, manager_member.agent_id, final_output, "task_result")
        await self._invoke_task_callback(task, final_output)

        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_completed" if passed else "task_partial",
            "data": {"task_id": task.id, "final_output": final_output, "manager_validation": manager_validation},
        })

    async def _run_group_chat_process(self, task: AgentGroupTask, group: AgentGroup) -> None:
        """Group chat process: agents discuss in rounds until consensus."""
        participants = [m for m in group.members if m.role in ("worker", "participant", "reviewer")]
        if not participants:
            participants = group.members[:]

        max_rounds = task.max_rounds or 5
        conversation: list[dict[str, Any]] = []
        consensus_reached = False

        for round_num in range(1, max_rounds + 1):
            async with async_session() as db:
                t = await db.get(AgentGroupTask, task.id)
                if t and t.status == "stopped":
                    return
                if t and t.status == "paused":
                    while t.status == "paused":
                        await asyncio.sleep(1)
                        t = await db.get(AgentGroupTask, task.id)
                        if not t or t.status in ("stopped", "failed"):
                            return

            await group_ws_hub.broadcast(task.group_id, {
                "type": "progress_update",
                "data": {"current_round": round_num, "max_rounds": max_rounds, "status": "running"},
            })

            for participant in participants:
                await group_ws_hub.broadcast(task.group_id, {
                    "type": "group_chat_turn",
                    "data": {"member_id": participant.id, "member_name": participant.agent_id, "round": round_num},
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
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                t.status = "completed" if consensus_reached else "partial"
                t.final_output = final_output
                t.completed_at = datetime.now(timezone.utc)
                await db.commit()

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
        review_tokens = 0
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                review_output, review_tokens = await self._run_agent_simple(
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

    async def _save_checkpoint(self, task_id: str, group_id: str, current_round: int, max_rounds: int, current_artifact: str, all_issues: list[dict[str, Any]]) -> None:
        """Save execution checkpoint for resume capability."""
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

    async def _load_latest_checkpoint(self, task_id: str) -> AgentGroupTaskCheckpoint | None:
        """Load the latest checkpoint for a task."""
        async with async_session() as db:
            result = (
                await db.execute(
                    select(AgentGroupTaskCheckpoint).where(
                        AgentGroupTaskCheckpoint.task_id == task_id
                    ).order_by(AgentGroupTaskCheckpoint.created_at.desc()).limit(1)
                )
            ).scalar_one_or_none()
            return result

    async def _resume_from_checkpoint(self, task: AgentGroupTask, checkpoint: AgentGroupTaskCheckpoint) -> None:
        """Resume task execution from a checkpoint."""
        # For now, mark as partial since full state restoration requires more complex logic
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t:
                t.status = "partial"
                t.final_output = checkpoint.current_artifact
                t.current_round = checkpoint.current_round
                t.completed_at = datetime.now(timezone.utc)
                await db.commit()
        await group_ws_hub.broadcast(task.group_id, {
            "type": "checkpoint_restored",
            "data": {"task_id": task.id, "checkpoint_id": checkpoint.id, "round": checkpoint.current_round},
        })
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_partial",
            "data": {"task_id": task.id, "final_output": checkpoint.current_artifact, "rounds": checkpoint.current_round},
        })

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

    async def _wait_for_human_review(self, task: AgentGroupTask, output: str) -> bool:
        """Wait for human review if required. Returns True if approved, False otherwise."""
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
                if t.status in ("stopped", "failed"):
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
            resolved_provider, resolved_model = MODEL_ALIASES[key]
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
                pass

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
