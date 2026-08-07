"""Group chat process implementation for group collaboration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select

from app.core.collaboration.agent_runner import run_agent_simple
from app.core.collaboration.callbacks import invoke_step_callback, invoke_task_callback
from app.core.collaboration.memory import store_memory
from app.core.collaboration.prompts import build_group_chat_context, build_group_chat_prompt, summarize_group_chat
from app.core.collaboration.resolver import resolve_api_key, resolve_base_url
from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupTask

logger = structlog.get_logger(__name__)


async def run_group_chat_process(task: Any, group: Any) -> None:
    """Group chat process: agents discuss in rounds until consensus."""
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

        await group_ws_hub.broadcast(task.group_id, {
            "type": "progress_update",
            "data": {"current_round": round_num, "max_rounds": max_rounds, "status": "running"},
        })

        await _execute_chat_round(task, participants, conversation, round_num)

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
) -> None:
    """Execute a single round of group chat."""
    from app.core.collaboration.constants import TASK_TIMEOUT

    for participant in participants:
        await group_ws_hub.broadcast(task.group_id, {
            "type": "group_chat_turn",
            "data": {"member_id": participant.id, "member_name": participant.agent_id, "round": round_num},
        })

        context_messages = build_group_chat_context(task.description, conversation)

        output = ""
        try:
            async with asyncio.timeout(TASK_TIMEOUT):
                output, tokens = await run_agent_simple(
                    agent_id=participant.agent_id,
                    provider=participant.model_provider or "openai",
                    model_id=participant.model_id or "gpt-4o",
                    api_key=resolve_api_key(participant.model_provider, participant.api_key_encrypted),
                    base_url=resolve_base_url(participant.model_provider, None),
                    system_prompt=build_group_chat_prompt(participant.role),
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
                "tokens_used": 0,
            },
        })

        await invoke_step_callback(task, participant.role, participant.agent_id, output)


def _check_consensus(participants: list[Any], conversation: list[dict[str, Any]]) -> bool:
    """Check if consensus is reached based on agreement keywords in recent messages."""
    recent = conversation[-(len(participants)):]
    agreement_count = sum(
        1 for m in recent
        if any(k in m["content"].lower() for k in ["同意", "agree", "consensus", "好的", "approved", "accept", "looks good"])
    )
    return agreement_count >= len(participants) * 0.6


async def _broadcast_completion(task: Any, consensus: bool, output: str, rounds: int) -> None:
    """Broadcast group chat completion."""
    await group_ws_hub.broadcast(task.group_id, {
        "type": "group_chat_consensus",
        "data": {"reached": consensus, "final_output": output},
    })
    await group_ws_hub.broadcast(task.group_id, {
        "type": "task_completed" if consensus else "task_partial",
        "data": {"task_id": task.id, "final_output": output, "rounds": rounds},
    })
