"""Message persistence for the agent engine."""

from __future__ import annotations

from typing import Any


async def persist_message(
    session_id: str,
    role: str,
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    tool_name: str | None = None,
    tokens: int = 0,
) -> None:
    """Persist a message to the database (fire-and-forget safe).

    Args:
        session_id: The session ID.
        role: The message role.
        content: The message content.
        tool_calls: Associated tool calls.
        tool_name: The tool name if this is a tool result.
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
                tokens=tokens,
            )
            db.add(msg)
            await db.commit()
    except Exception:
        pass
