"""Memory tools for LLM self-directed memory management.

- Letta `memory` 工具链（core/memory.py）
- Hermes-Agent 记忆系统
"""

from __future__ import annotations

from typing import Any

from app.core.persistent_memory import persistent_memory
from app.tools import tool


@tool(description="Store an important memory about the user or conversation for later retrieval.")
async def store_memory(content: str, importance: float = 0.5, memory_type: str = "observation") -> str:
    """Store a memory for later retrieval.

    Args:
        content: The memory content to store.
        importance: Importance score 0.0-1.0. Default 0.5.
        memory_type: Type: preference, fact, decision, observation. Default: observation.
    """
    if not content:
        return "Error: content is required"
    try:
        mem = await persistent_memory.create_episodic_memory(
            user_id="default-user",
            content=content,
            memory_type=memory_type,
            importance=importance,
        )
        return f"Memory stored (id={mem.id}, importance={importance})"
    except Exception as e:
        return f"Error storing memory: {e}"


@tool(description="Search stored memories by semantic query.")
async def search_memories(query: str, limit: int = 5) -> str:
    """Search memories by query.

    Args:
        query: Search query string.
        limit: Max results. Default 5.
    """
    if not query:
        return "Error: query is required"
    try:
        memories = await persistent_memory.retrieve_memories(
            user_id="default-user",
            query=query,
            limit=limit,
        )
        if not memories:
            return "No memories found."
        lines = [f"Found {len(memories)} memories:"]
        for m in memories:
            lines.append(f"- [{m.memory_type}] {m.content[:200]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching memories: {e}"


@tool(description="Remember a persistent fact about the user for future sessions.")
async def remember_user_fact(fact: str, category: str = "general") -> str:
    """Remember a user fact.

    Args:
        fact: The fact to remember.
        category: Category: personal, work, preference, general. Default: general.
    """
    if not fact:
        return "Error: fact is required"
    try:
        profile = await persistent_memory.add_user_fact(
            user_id="default-user",
            fact=fact,
            category=category,
        )
        return f"User fact remembered (category={category})"
    except Exception as e:
        return f"Error remembering fact: {e}"
