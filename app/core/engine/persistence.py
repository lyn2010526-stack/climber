"""Message persistence for the agent engine."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def persist_message(
    session_id: str,
    role: str,
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    tokens: int = 0,
) -> None:
    """Persist a message to the database (fire-and-forget safe).

    Args:
        session_id: The session ID.
        role: The message role.
        content: The message content.
        tool_calls: Associated tool calls.
        tool_name: The tool name if this is a tool result.
        tool_call_id: ID linking a tool result to its tool call.
        tokens: Token count for this message.
    """
    try:
        from app.storage import async_session
        from app.storage.database import Message

        async with async_session() as db:
            msg = Message(
                session_id=session_id,
                role=role,
                content=content,
                tool_calls=tool_calls or [],
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                tokens=tokens,
            )
            db.add(msg)
            await db.commit()
    except Exception:
        logger.exception("Failed to persist session message", extra={"session_id": session_id})
