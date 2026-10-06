"""Group chat process implementation for group collaboration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.collaboration import agent_runner
from app.core.collaboration.callbacks import invoke_step_callback, invoke_task_callback
from app.core.collaboration.memory import store_memory
from app.core.collaboration.prompts import (
    build_group_chat_context,
    build_group_chat_prompt,
    summarize_group_chat,
)
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask

logger = structlog.get_logger(__name__)


async def run_group_chat_process(task: Any, group: Any, principal: Any = None) -> None:
    """Group chat process: agents discuss in rounds until consensus.

    Args:
        task: The task entity to execute.
        group: The group entity (used to resolve the execution principal).
        principal: Explicit principal propagated to every agent call; resolved
            from the group owner when omitted.

    Raises:
        Exception: Any agent failure is re-raised so ``run_task`` marks the
            task failed; errors are never spoken into the conversation.
    """
    principal = principal or agent_runner.principal_for_group(group)
    participants = [m for m in group.members if m.role in ("worker", "participant", "reviewer")]
    if not participants:
        participants = group.members[:]

    max_rounds = task.max_rounds or 5
    conversation: list[dict[str, Any]] = []
    consensus_reached = False
    final_round = 0

    for round_num in range(1, max_rounds + 1):
        if not await _check_task_not_stopped(task):
            return

        await group_ws_hub.broadcast(
            task.group_id,
            {
                "type": "progress_update",
                "data": {"current_round": round_num, "max_rounds": max_rounds, "status": "running"},
            },
        )

        await _execute_chat_round(task, participants, conversation, round_num, principal=principal)

        if round_num >= 2 and _check_consensus(participants, conversation):
            consensus_reached = True
            final_round = round_num
            break

    final_output = summarize_group_chat(task.description, conversation)
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t:
            t.status = "completed" if consensus_reached else "partial"
            t.final_output = final_output
            t.completed_at = datetime.now(UTC)
            await db.commit()

    await store_memory(task.group_id, task.id, "group_chat", final_output, "task_result")
    await invoke_task_callback(task, final_output)

    await _broadcast_completion(task, consensus_reached, final_output, final_round or max_rounds)


async def _check_task_not_stopped(task: Any) -> bool:
    """Check task status and wait if paused."""
    async with async_session() as db:
        t = await db.get(AgentGroupTask, task.id)
        if t and t.status == "stopped":
            return False
        if t and t.status == "paused":
            while t.status == "paused":
                await asyncio.sleep(1)
                t = await db.get(AgentGroupTask, task.id)
                if not t or t.status in ("stopped", "failed"):
                    return False
    return True


async def _execute_chat_round(
    task: Any,
    participants: list[Any],
    conversation: list[dict[str, Any]],
    round_num: int,
    principal: Any = None,
) -> None:
    """Execute a single round of group chat.

    Args:
        task: The task entity.
        participants: Members participating in the chat.
        conversation: Conversation history (appended in place).
        round_num: Current round number.
        principal: Explicit principal for every participant call.

    Raises:
        Exception: Any agent failure is re-raised to the caller (``run_task``
            marks the task failed) instead of being spoken as a message.
    """
    from app.core.collaboration.constants import TASK_TIMEOUT

    for participant in participants:
        await group_ws_hub.broadcast(
            task.group_id,
            {
                "type": "group_chat_turn",
                "data": {
                    "member_id": participant.id,
                    "member_name": participant.agent_id,
                    "round": round_num,
                },
            },
        )

        context_messages = build_group_chat_context(task.description, conversation)

        async with asyncio.timeout(TASK_TIMEOUT):
            output, tokens_used = await agent_runner.run_agent_simple(
                agent_id=participant.agent_id,
                provider=participant.model_provider or "openai",
                model_id=participant.model_id or "gpt-4o",
                api_key=resolve_api_key(participant.model_provider, participant.api_key_encrypted),
                base_url=resolve_base_url(participant.model_provider, None),
                system_prompt=build_group_chat_prompt(participant.role),
                user_message=context_messages,
                tools=participant.tools or [],
                group_id=task.group_id,
                role=participant.role,
                principal=principal,
                task_name=task.description,
            )

        conversation.append(
            {
                "round": round_num,
                "agent_id": participant.agent_id,
                "agent_name": participant.agent_id,
                "role": participant.role,
                "content": output,
            }
        )

        await group_ws_hub.broadcast(
            task.group_id,
            {
                "type": "message",
                "data": {
                    "sender_id": participant.agent_id,
                    "sender_name": participant.agent_id,
                    "content": output,
                    "message_type": "text",
                    "round": round_num,
                    "tokens_used": tokens_used,
                },
            },
        )

        await invoke_step_callback(task, participant.role, participant.agent_id, output)


def _check_consensus(participants: list[Any], conversation: list[dict[str, Any]]) -> bool:
    """Check if consensus is reached based on agreement keywords in recent messages.

    Messages that express disagreement (e.g. "disagree", "不同意") are excluded
    even though they contain agreement substrings like "agree" / "同意".
    """
    recent = conversation[-(len(participants)) :]

    agreement_keywords = ["同意", "agree", "consensus", "好的", "approved", "accept", "looks good"]
    disagreement_keywords = [
        "不同意",
        "不赞同",
        "反对",
        "cannot agree",
        "can't agree",
        "do not agree",
        "don't agree",
        "disagree",
        "not agree",
        "reject",
    ]

    agreement_count = 0
    for m in recent:
        content = m["content"].lower()
        if any(k in content for k in disagreement_keywords):
            continue
        if any(k in content for k in agreement_keywords):
            agreement_count += 1

    return agreement_count >= len(participants) * 0.6


async def _broadcast_completion(task: Any, consensus: bool, output: str, rounds: int) -> None:
    """Broadcast group chat completion."""
    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "group_chat_consensus",
            "data": {"reached": consensus, "final_output": output},
        },
    )
    await group_ws_hub.broadcast(
        task.group_id,
        {
            "type": "task_completed" if consensus else "task_partial",
            "data": {"task_id": task.id, "final_output": output, "rounds": rounds},
        },
    )
