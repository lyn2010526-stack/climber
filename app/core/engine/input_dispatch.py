"""Explicit idle dispatch; committed history only, never checkpoint replay."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import or_, select, update

from app.storage.database import Message, Session, SessionInput, Turn

if TYPE_CHECKING:
    from app.core.engine.input_queue import SessionInputQueue


class InputDispatchConflict(ValueError):
    pass


async def prepare_dispatch(
    queue: "SessionInputQueue",
    session_id: str,
    user_id: str,
    *,
    claim: bool = False,
    session: Any = None,
) -> dict[str, Any]:
    async with queue.session_factory() as db:
        # Serialize the safety check and first claim with queue producers/consumers.
        result = await db.execute(
            update(Session)
            .where(
                Session.id == session_id,
                Session.user_id == user_id,
            )
            .values(updated_at=Session.updated_at)
        )
        if result.rowcount != 1:
            raise LookupError("Session not found")
        row = await db.get(Session, session_id)
        if (row.context_data or {}).get("input_queue_frozen"):
            raise InputDispatchConflict("Queue is frozen; explicit review is required")
        started = await db.scalar(
            select(SessionInput.id)
            .where(
                SessionInput.session_id == session_id,
                SessionInput.status == "started",
            )
            .limit(1)
        )
        unfinished = await db.scalar(
            select(Turn.id)
            .where(
                Turn.session_id == session_id,
                or_(
                    Turn.status.in_(("pending", "running")),
                    (Turn.status == "paused") & Turn.completed_at.is_(None),
                ),
            )
            .limit(1)
        )
        if started or unfinished:
            raise InputDispatchConflict(
                "Interrupted execution requires review; queue start cannot replay it"
            )
        item = await db.scalar(
            select(SessionInput)
            .where(
                SessionInput.session_id == session_id,
                SessionInput.kind == "follow_up",
                SessionInput.status == "queued",
            )
            .order_by(SessionInput.sequence)
            .limit(1)
        )
        if item is None:
            raise InputDispatchConflict(
                "No queued follow-up task; steering requires an active task"
            )
        if claim:
            if session is not None:
                history = (
                    await db.scalars(
                        select(Message)
                        .where(
                            Message.session_id == session_id,
                        )
                        .order_by(Message.created_at, Message.id)
                    )
                ).all()
                session.messages = [
                    message for message in session.messages if message.get("role") == "system"
                ]
                for message in history:
                    entry = {"role": message.role, "content": message.content or ""}
                    if message.tool_calls:
                        entry["tool_calls"] = message.tool_calls
                    if message.tool_call_id:
                        entry["tool_call_id"] = message.tool_call_id
                    session.messages.append(entry)
                session.current_turn_id = None
                session._resume_interrupted = False
                session._stop_requested = False
                session._restore_status("pending")
            item.status = "started"
        from app.core.engine.input_queue import input_item

        payload = input_item(item)
        await db.commit()
        return payload
