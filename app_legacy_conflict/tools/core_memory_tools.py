"""Core Memory tools — LLM self-directed core memory management.

- Letta `core_memory_append` / `core_memory_replace` tools
- Hermes-Agent memory tools
"""

from __future__ import annotations

from typing import Any

from app.core.core_memory import core_memory
from app.tools import tool


@tool(description="Append text to a core memory block. The LLM can use this to update its own persona or user profile.")
async def core_memory_append(label: str, text: str, user_id: str = "default-user", agent_id: str | None = None) -> str:
    """Append text to a core memory block.

    Args:
        label: Memory block label (e.g., persona, user_profile).
        text: Text to append.
        user_id: User identifier.
        agent_id: Optional agent identifier.
    """
    if not label or not text:
        return "Error: label and text are required"
    try:
        block = await core_memory.append_block(user_id=user_id, label=label, text=text, agent_id=agent_id)
        if block is None:
            return f"Error: block '{label}' not found and could not be created"
        return f"Appended to core memory block '{label}' (new length: {len(block.value)})"
    except Exception as e:
        return f"Error appending to core memory: {e}"


@tool(description="Replace text in a core memory block. The LLM can use this to correct or update its own memory.")
async def core_memory_replace(label: str, old_text: str, new_text: str, user_id: str = "default-user", agent_id: str | None = None) -> str:
    """Replace text in a core memory block.

    Args:
        label: Memory block label.
        old_text: Text to replace (must exist exactly once).
        new_text: Replacement text.
        user_id: User identifier.
        agent_id: Optional agent identifier.
    """
    if not label or old_text is None or new_text is None:
        return "Error: label, old_text, and new_text are required"
    try:
        block = await core_memory.replace_in_block(user_id=user_id, label=label, old_text=old_text, new_text=new_text, agent_id=agent_id)
        if block is None:
            return f"Error: block '{label}' not found"
        return f"Replaced text in core memory block '{label}' (new length: {len(block.value)})"
    except Exception as e:
        return f"Error replacing core memory: {e}"


@tool(description="Create a new core memory block with initial value.")
async def core_memory_create(label: str, value: str, user_id: str = "default-user", agent_id: str | None = None, description: str = "", read_only: bool = False) -> str:
    """Create a new core memory block.

    Args:
        label: Memory block label.
        value: Initial block content.
        user_id: User identifier.
        agent_id: Optional agent identifier.
        description: Human-readable description of this block.
        read_only: Whether the LLM can modify this block.
    """
    if not label or not value:
        return "Error: label and value are required"
    try:
        block = await core_memory.create_or_update_block(
            user_id=user_id,
            label=label,
            value=value,
            agent_id=agent_id,
            description=description,
            read_only=read_only,
        )
        return f"Created core memory block '{label}' (length: {len(block.value)})"
    except Exception as e:
        return f"Error creating core memory block: {e}"
