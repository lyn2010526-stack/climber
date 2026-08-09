"""Sequential process implementation for group collaboration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.collaboration.agent_runner import run_agent_with_retry
from app.core.collaboration.callbacks import invoke_step_callback, invoke_task_callback, wait_for_human_review
from app.core.collaboration.checkpoint import save_checkpoint
from app.core.collaboration.guardrails import run_guardrails
from app.core.collaboration.memory import build_context_from_dependencies, inject_memory, merge_context, store_memory
from app.core.collaboration.prompts import (
    build_initial_prompt,
    build_review_prompt,
    build_reviewer_prompt,
    build_sequential_prompt,
    build_worker_prompt,
)
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask

logger = structlog.get_logger(__name__)


async def run_sequential_process(
    task: Any,
    worker: Any,
    reviewers: list[Any],
    group: Any,
    max_rounds: int,
) -> None:
    """Execute sequential task with iterative refinement.

    Each round produces worker output, runs guardrails, and optionally
    collects reviewer feedback. Continues until no issues remain or max
    rounds reached.
    """
    context_data = await build_context_from_dependencies(task)
    memory_context = await inject_memory(task.group_id, task.id, task.description)
    full_context = merge_context(context_data, memory_context)

    current_round = 0
    worker_output = ""
    all_issues: list[dict[str, Any]] = []

    try:
        while current_round < max_rounds:
            if not await _refresh_task_state(task):
                return

            current_round += 1
            await _update_round_status(task, current_round, max_rounds, worker)

            worker_output, worker_tokens = await _execute_worker_turn(
                task, worker, full_context, worker_output, all_issues, current_round
            )

            if not worker_output:
                return

            await _broadcast_worker_done(task, worker, worker_output, worker_tokens)
            await invoke_step_callback(task, "worker", worker.agent_id, worker_output)

            guardrail_passed, guardrail_feedback = await run_guardrails(task, worker_output)
            if not guardrail_passed:
                all_issues = guardrail_feedback
                await _broadcast_guardrail_retry(task, current_round, guardrail_feedback)
                continue

            if task.human_review_required:
                approved = await wait_for_human_review(task, worker_output)
                if not approved:
                    all_issues = [{"description": "Human review rejected or timed out", "severity": "high"}]
                    await _broadcast_human_review_rejected(task, current_round)
                    continue

            all_issues = []
            reviewer_results = await _execute_reviewer_turn(
                task, reviewers, worker_output, worker_tokens
            )
            all_issues.extend(reviewer_results)

            if not all_issues and await _validate_and_finalize(task, worker_output):
                await store_memory(task.group_id, task.id, worker.agent_id, worker_output, "task_result")
                await invoke_task_callback(task, worker_output)
                await _checkpoint_and_broadcast(task, current_round, worker_output, [])
                await _broadcast_task_completed(task, worker_output, current_round)
                return

            await _checkpoint_and_broadcast(task, current_round, worker_output, all_issues)

        await _mark_task_partial(task, worker_output, current_round)

    except Exception as e:
        logger.exception("group_task_failed", task_id=task.id)
        await _mark_task_failed(task, str(e))


async def _refresh_task_state(task: Any) -> bool:
    """Refresh task state from DB, return False if task should stop."""
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t is None:
            logger.error("task_disappeared", task_id=task.id)
            return False
        if t.status == "stopped":
            return False
        if t.status == "paused" and not await _wait_while_paused(t):
            return False
        task.__dict__.update(t.__dict__)
        return True


async def _wait_while_paused(task: Any) -> bool:
    """Wait while task is paused, return False if task should stop."""
    while task.status == "paused":
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_update",
            "data": {"id": task.id, "status": "paused"},
        })
        await asyncio.sleep(1)
        async with async_session() as db:
            t = await db.get(AgentGroupTask, task.id)
            if t is None or t.status in ("stopped", "failed", "completed"):
                return False
            task.__dict__.update(t.__dict__)
    return True


async def _update_round_status(task: Any, current_round: int, max_rounds: int, worker: Any) -> None:
    """Update task status and broadcast round start."""
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.current_round = current_round
            t.status = "running"
            await db.commit()

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


async def _execute_worker_turn(
    task: Any,
    worker: Any,
    full_context: str,
    worker_output: str,
    all_issues: list[dict[str, Any]],
    current_round: int,
) -> tuple[str, int]:
    """Execute a single worker turn with retry."""
    user_message = (
        build_sequential_prompt(task.description, full_context, worker_output, all_issues)
        if current_round > 1
        else build_initial_prompt(task.description, full_context)
    )

    try:
        output, tokens = await run_agent_with_retry(
            agent_id=worker.agent_id,
            provider=worker.model_provider or "openai",
            model_id=worker.model_id or "gpt-4o",
            api_key=resolve_api_key(worker.model_provider, worker.api_key_encrypted),
            system_prompt=build_worker_prompt(task.description),
            user_message=user_message,
            tools=worker.tools or [],
            group_id=task.group_id,
            role="worker",
            base_url=resolve_base_url(worker.model_provider, None),
        )
        if not output:
            raise Exception("worker returned empty output after retry")
        return output, tokens
    except Exception as e:
        logger.error("worker_failed", task_id=task.id, round=current_round, error=str(e))
        await group_ws_hub.broadcast(task.group_id, {
            "type": "task_failed",
            "data": {"task_id": task.id, "error": f"Worker failed after retry: {e}"},
        })
        return "", 0


async def _broadcast_worker_done(task: Any, worker: Any, output: str, tokens: int) -> None:
    """Broadcast worker completion."""
    await group_ws_hub.broadcast(task.group_id, {
        "type": "worker_done",
        "data": {
            "member_id": worker.id,
            "member_name": worker.agent_id,
            "content": output,
            "tokens_used": tokens,
        },
    })


async def _broadcast_guardrail_retry(task: Any, round_num: int, feedback: list) -> None:
    """Broadcast guardrail retry."""
    await group_ws_hub.broadcast(task.group_id, {
        "type": "guardrail_retry",
        "data": {"round": round_num, "feedback": feedback},
    })


async def _broadcast_human_review_rejected(task: Any, round_num: int) -> None:
    """Broadcast human review rejection."""
    await group_ws_hub.broadcast(task.group_id, {
        "type": "human_review_rejected",
        "data": {"round": round_num},
    })


async def _execute_reviewer_turn(
    task: Any,
    reviewers: list[Any],
    worker_output: str,
    worker_tokens: int,
) -> list[dict[str, Any]]:
    """Execute reviewer turns and collect issues."""
    from app.core.collaboration.constants import TASK_TIMEOUT

    all_issues: list[dict[str, Any]] = []
    for reviewer in reviewers:
        await group_ws_hub.broadcast(task.group_id, {
            "type": "reviewer_start",
            "data": {"member_id": reviewer.id, "member_name": reviewer.agent_id},
        })

        review_output = ""
        review_error = None
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                review_output, review_tokens = await __import__("app.core.collaboration.agent_runner", fromlist=["run_agent_simple"]).run_agent_simple(
                    agent_id=reviewer.agent_id,
                    provider=reviewer.model_provider or "openai",
                    model_id=reviewer.model_id or "gpt-4o",
                    api_key=resolve_api_key(reviewer.model_provider, reviewer.api_key_encrypted),
                    base_url=resolve_base_url(reviewer.model_provider, None),
                    system_prompt=build_reviewer_prompt(task.description),
                    user_message=build_review_prompt(task.description, worker_output),
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
        issues = __import__("app.core.collaboration.guardrails", fromlist=["_parse_issues"])._parse_issues(review_output)

        await group_ws_hub.broadcast(task.group_id, {
            "type": "reviewer_done",
            "data": {
                "member_id": reviewer.id,
                "member_name": reviewer.agent_id,
                "passed": passed,
                "issues": issues,
                "content": review_output,
                "tokens_used": 0,
            },
        })

        if not passed:
            all_issues.extend(issues)

    return all_issues


async def _validate_and_finalize(task: Any, worker_output: str) -> bool:
    """Validate structured output if schema provided. Returns True if valid."""
    from app.core.collaboration.guardrails import validate_structured_output

    if task.output_schema:
        valid, parsed = validate_structured_output(worker_output, task.output_schema)
        if not valid:
            await group_ws_hub.broadcast(task.group_id, {
                "type": "guardrail_failed",
                "data": {"reason": "structured_output_validation_failed", "details": parsed},
            })
            return False

    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "completed"
            t.final_output = worker_output
            if task.output_schema:
                t.structured_output = parsed if 'parsed' in dir() else {}
            t.completed_at = datetime.now(UTC)
            await db.commit()
    return True


async def _checkpoint_and_broadcast(task: Any, round_num: int, output: str, issues: list) -> None:
    """Save checkpoint and broadcast."""
    await save_checkpoint(task.id, task.group_id, round_num, task.max_rounds or 5, output, issues)
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_checkpoint",
        "data": {"task_id": task.id, "round": round_num},
    })


async def _broadcast_task_completed(task: Any, output: str, rounds: int) -> None:
    """Broadcast task completion."""
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_completed",
        "data": {"task_id": task.id, "final_output": output, "rounds": rounds},
    })


async def _mark_task_partial(task: Any, output: str, rounds: int) -> None:
    """Mark task as partial (max rounds reached with issues)."""
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "partial"
            t.final_output = output
            t.completed_at = datetime.now(UTC)
            await db.commit()
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_partial",
        "data": {"task_id": task.id, "final_output": output, "rounds": rounds},
    })


async def _mark_task_failed(task: Any, error: str) -> None:
    """Mark task as failed."""
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
        "data": {"task_id": task.id, "error": error},
    })
