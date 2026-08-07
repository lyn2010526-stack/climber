"""Memory management for group collaboration."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select

from app.core.group_ws_hub import group_ws_hub
from app.storage import async_session
from app.storage.models_groups import AgentGroupMemory

logger = structlog.get_logger(__name__)


async def inject_memory(group_id: str, task_id: str, query: str) -> str:
    """Retrieve relevant memories and format them for prompt injection.

    Args:
        group_id: The group ID to search memories for.
        task_id: The current task ID for broadcast context.
        query: The query to find relevant memories.

    Returns:
        A formatted string of relevant memories, or empty string if none found.
    """
    async with async_session() as db:
        memories = (
            await db.execute(
                select(AgentGroupMemory)
                .where(
                    AgentGroupMemory.group_id == group_id,
                    AgentGroupMemory.memory_type.in_(["short_term", "long_term"]),
                )
                .order_by(AgentGroupMemory.importance.desc(), AgentGroupMemory.created_at.desc())
                .limit(10)
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


async def store_memory(
    group_id: str,
    task_id: str,
    agent_id: str,
    content: str,
    memory_type: str = "task_result",
) -> None:
    """Store a memory entry for future retrieval.

    Args:
        group_id: The group ID.
        task_id: The task ID.
        agent_id: The agent that produced the content.
        content: The full content to store.
        memory_type: The category of memory.
    """
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


async def build_context_from_dependencies(task: Any) -> dict[str, Any]:
    """Build context from tasks listed in the `context` field.

    Args:
        task: The AgentGroupTask entity with context field.

    Returns:
        A dictionary mapping task IDs to their output context.
    """
    context_data: dict[str, Any] = {}
    if not task.context:
        return context_data
    async with async_session() as db:
        for dep_task_id in task.context:
            dep_task = await db.get(__import__("app.storage.models_groups", fromlist=["AgentGroupTask"]).AgentGroupTask, dep_task_id)
            if dep_task and dep_task.final_output:
                context_data[dep_task_id] = {
                    "description": dep_task.description,
                    "output": dep_task.final_output,
                    "status": dep_task.status,
                    "completed_at": dep_task.completed_at.isoformat() if dep_task.completed_at else None,
                }
    return context_data


def merge_context(context_data: dict[str, Any], memory_context: str) -> str:
    """Merge task context and memory context into a single string.

    Args:
        context_data: Dictionary of task dependency outputs.
        memory_context: Formatted memory context string.

    Returns:
        A merged context string for prompt injection.
    """
    parts = []
    if context_data:
        parts.append("Context from previous tasks:")
        for task_id, ctx in context_data.items():
            parts.append(f"- Task {task_id}: {ctx.get('output', '')[:500]}")
    if memory_context:
        parts.append(memory_context)
    return "\n\n".join(parts)
