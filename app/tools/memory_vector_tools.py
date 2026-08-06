"""Vector memory tools for LLM self-directed memory management.

- Letta `memory` tool chain with vector search
- Suna lightweight vector memory
- Hermes-Agent reflection memory
"""

from __future__ import annotations

from typing import Any

from app.core.memory_reflection import memory_reflection
from app.core.memory_tool_context import get_memory_tool_context
from app.core.persistent_memory import persistent_memory
from app.core.vector_memory import vector_memory
from app.tools import tool


@tool(description="Store a memory with vector embedding for later semantic retrieval.")
async def register_memories(content: str, importance: float = 0.5, memory_type: str = "observation", tags: list[str] | None = None) -> str:
    """Store a memory for later retrieval with vector search.

    Args:
        content: The memory content to store.
        importance: Importance score 0.0-1.0. Default 0.5.
        memory_type: Type: preference, fact, decision, observation. Default: observation.
        tags: Optional tags for filtering.
    """
    if not content:
        return "Error: content is required"
    try:
        ctx = get_memory_tool_context()
        mem = await persistent_memory.create_episodic_memory(
            user_id=ctx.user_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
        )
        await vector_memory.add(
            collection="episodic",
            doc_id=mem.id,
            text=content,
            metadata={
                "user_id": ctx.user_id,
                "memory_id": mem.id,
                "memory_type": memory_type,
                "importance": importance,
                "tags": tags or [],
            },
        )
        return f"Memory registered with vector search (id={mem.id}, importance={importance})"
    except Exception as e:
        return f"Error registering memory: {e}"


@tool(description="Recall memories by semantic similarity to a query.")
async def recall_memories(query: str, limit: int = 5, memory_type: str | None = None) -> str:
    """Search memories by semantic similarity.

    Args:
        query: Search query string.
        limit: Max results. Default 5.
        memory_type: Optional filter by memory type.
    """
    if not query:
        return "Error: query is required"
    try:
        ctx = get_memory_tool_context()
        where: dict[str, Any] | None = {"user_id": ctx.user_id}
        if memory_type:
            where = {"user_id": ctx.user_id, "memory_type": memory_type}

        vector_results = await vector_memory.search(
            collection="episodic",
            query=query,
            top_k=limit,
            where=where,
        )

        if not vector_results:
            memories = await persistent_memory.retrieve_memories(
                user_id=ctx.user_id,
                query=query,
                limit=limit,
            )
            if not memories:
                return "No memories found."
            lines = [f"Found {len(memories)} memories (keyword fallback):"]
            for m in memories:
                lines.append(f"- [{m.memory_type}] {m.content[:200]}")
            return "\n".join(lines)

        lines = [f"Found {len(vector_results)} memories:"]
        for r in vector_results:
            tags = r["metadata"].get("tags", [])
            tag_str = f", tags={tags}" if tags else ""
            lines.append(f"- [{r['metadata'].get('memory_type', 'unknown')}] {r['text'][:200]} (score={r['score']:.3f}{tag_str})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error recalling memories: {e}"


@tool(description="Reflect on a completed task and store insights for future tasks.")
async def reflect_on_task(
    task_description: str,
    outcome: str,
    success: bool = True,
    blockers: list[str] | None = None,
    improvements: list[str] | None = None,
) -> str:
    """Record a structured reflection after completing a task.

    Args:
        task_description: Description of the completed task.
        outcome: Result of the task.
        success: Whether the task succeeded. Default True.
        blockers: List of blockers encountered.
        improvements: List of improvements for next time.
    """
    if not task_description or not outcome:
        return "Error: task_description and outcome are required"
    try:
        ctx = get_memory_tool_context()
        result = await memory_reflection.reflect_on_task(
            user_id=ctx.user_id,
            task_description=task_description,
            outcome=outcome,
            success=success,
            blockers=blockers,
            improvements=improvements,
        )
        similar = await memory_reflection.get_similar_reflections(
            user_id=ctx.user_id,
            task_description=task_description,
            limit=3,
        )
        response = f"Reflection recorded (id={result['memory_id']})"
        if similar:
            response += f"\nSimilar past reflections: {len(similar)}"
            for s in similar[:3]:
                response += f"\n- {s['text'][:150]} (score={s['score']:.3f})"
        return response
    except Exception as e:
        return f"Error reflecting on task: {e}"
