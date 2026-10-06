"""Committed session inputs; session-row writes serialize producers and consumers."""

from __future__ import annotations

import json

from sqlalchemy import func, select, update

from app.storage.database import Session, SessionInput


def stalled_batch(calls, results):
    """Only explicitly read-only tools can establish unchanged-work evidence."""
    if not calls or len(calls) != len(results):
        return None
    evidence = []
    if any(
        not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]
        for item in [*calls, *results]
    ):
        return None
    by_id = {result["id"]: result for result in results}
    call_ids = {call["id"] for call in calls}
    if len(call_ids) != len(calls) or len(by_id) != len(results) or call_ids != by_id.keys():
        return None
    for call in calls:
        result = by_id.get(call.get("id"))
        if result is None:
            return None
        function = call.get("function", {})
        if not isinstance(function, dict):
            return None
        # Local observations/pure transforms only; side-effecting tools always count as progress.
        if function.get("name") not in {
            "read_file",
            "list_files",
            "file_exists",
            "file_info",
            "file_diff",
            "calculator",
            "json_get",
            "base64_encode",
        }:
            return None
        if result.get("error") or not str(result.get("result") or "").strip():
            return None
        if str(result["result"]).strip().lower().startswith("error"):
            return None
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                return None
        if not isinstance(arguments, dict):
            return None
        evidence.append((function.get("name"), arguments, result.get("result")))
    return json.dumps(evidence, sort_keys=True, default=str)


def input_item(row):
    return {
        key: getattr(row, key)
        for key in (
            "id",
            "client_request_id",
            "kind",
            "message",
            "status",
            "sequence",
            "error",
        )
    }


class SessionInputQueue:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def _lock(self, db, session_id, user_id):
        # Acquire the writer lock before reading: also avoids SQLite lock upgrades.
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
        return await db.get(Session, session_id)

    async def submit(self, session_id, user_id, client_request_id, kind, message):
        async with self.session_factory() as db:
            session = await self._lock(db, session_id, user_id)
            existing = await db.scalar(
                select(SessionInput).where(
                    SessionInput.session_id == session_id,
                    SessionInput.client_request_id == client_request_id,
                )
            )
            if existing is not None:
                if existing.kind != kind or existing.message != message:
                    raise ValueError("client_request_id already used with different input")
                await db.commit()
                return input_item(existing)
            sequence = (
                await db.scalar(
                    select(func.max(SessionInput.sequence)).where(
                        SessionInput.session_id == session_id,
                    )
                )
                or 0
            ) + 1
            reason = (session.context_data or {}).get("input_queue_frozen")
            row = SessionInput(
                session_id=session_id,
                client_request_id=client_request_id,
                kind=kind,
                message=message,
                sequence=sequence,
                status="blocked" if reason else "queued",
                error=reason,
            )
            db.add(row)
            if reason:
                await db.flush()
                context = dict(session.context_data or {})
                session.context_data = {
                    **context,
                    "input_queue_safe_to_resume": [
                        *context.get("input_queue_safe_to_resume", []),
                        row.id,
                    ],
                }
            await db.commit()
            return input_item(row)

    async def list(self, session_id, user_id):
        async with self.session_factory() as db:
            owner = await db.scalar(
                select(Session.id).where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                )
            )
            if owner is None:
                raise LookupError("Session not found")
            rows = (
                await db.scalars(
                    select(SessionInput)
                    .where(
                        SessionInput.session_id == session_id,
                    )
                    .order_by(SessionInput.sequence)
                )
            ).all()
            return [input_item(row) for row in rows]

    async def claim(self, session_id, user_id, kind):
        async with self.session_factory() as db:
            session = await self._lock(db, session_id, user_id)
            if (session.context_data or {}).get("input_queue_frozen"):
                await db.commit()
                return None
            row = await db.scalar(
                select(SessionInput)
                .where(
                    SessionInput.session_id == session_id,
                    SessionInput.kind == kind,
                    SessionInput.status == "queued",
                )
                .order_by(SessionInput.sequence)
                .limit(1)
            )
            if row is not None:
                row.status = "started"
            await db.commit()
            return input_item(row) if row else None

    async def report(self, session_id, user_id, active_message=None):
        async with self.session_factory() as db:
            session = await db.scalar(
                select(Session).where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                )
            )
            if session is None:
                raise LookupError("Session not found")
            rows = (
                await db.scalars(
                    select(SessionInput)
                    .where(
                        SessionInput.session_id == session_id,
                    )
                    .order_by(SessionInput.sequence)
                )
            ).all()
            report = {"completed": [], "executing": [], "queued": [], "risks": []}
            categories = {
                "completed": "completed",
                "applied": "completed",
                "started": "executing",
                "queued": "queued",
                "blocked": "risks",
                "failed": "risks",
            }
            for row in rows:
                text = row.message
                if row.status in {"blocked", "failed"}:
                    text = f"{row.message}: {row.error or row.status}"
                report[categories[row.status]].append(text)
            if active_message is not None:
                report["executing"].insert(0, active_message)
            reason = (session.context_data or {}).get("input_queue_frozen")
            if reason and not report["risks"]:
                report["risks"].append(reason)
            return report

    async def finish(self, session_id, user_id, input_id, status, error=None):
        if status not in {"applied", "completed", "blocked", "failed"}:
            raise ValueError("Invalid input terminal status")
        async with self.session_factory() as db:
            await self._lock(db, session_id, user_id)
            row = await db.scalar(
                select(SessionInput).where(
                    SessionInput.id == input_id,
                    SessionInput.session_id == session_id,
                )
            )
            if row is None:
                raise RuntimeError("Input is no longer started")
            # A concurrent safety freeze is authoritative over late acknowledgements.
            if row.status == "blocked" or row.status == status:
                await db.commit()
                return input_item(row)
            if row.status != "started":
                raise RuntimeError("Input is no longer started")
            row.status, row.error = status, error
            await db.commit()
            return input_item(row)

    async def freeze(self, session_id, user_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("A nonempty freeze reason is required")
        async with self.session_factory() as db:
            session = await self._lock(db, session_id, user_id)
            rows = await self._freeze(db, session, reason)
            await db.commit()
            return [input_item(row) for row in rows]

    async def _freeze(self, db, session, reason):
        context = dict(session.context_data or {})
        rows = (
            await db.scalars(
                select(SessionInput)
                .where(
                    SessionInput.session_id == session.id,
                    SessionInput.status.in_(("queued", "started")),
                )
                .order_by(SessionInput.sequence)
            )
        ).all()
        safe_ids = set(context.get("input_queue_safe_to_resume", []))
        for row in rows:
            if row.status == "queued":
                safe_ids.add(row.id)
            else:
                safe_ids.discard(row.id)
            row.status, row.error = "blocked", reason
        session.context_data = {
            **context,
            "input_queue_frozen": reason,
            "input_queue_safe_to_resume": sorted(safe_ids),
        }
        return rows

    async def resume_reviewed(self, session_id, user_id, review_confirmed):
        async with self.session_factory() as db:
            session = await self._lock(db, session_id, user_id)
            if review_confirmed is not True:
                raise ValueError("Explicit review confirmation is required")
            context = dict(session.context_data or {})
            safe_ids = set(context.pop("input_queue_safe_to_resume", []))
            context.pop("input_queue_frozen", None)
            rows = (
                await db.scalars(
                    select(SessionInput)
                    .where(
                        SessionInput.session_id == session_id,
                    )
                    .order_by(SessionInput.sequence)
                )
            ).all()
            for row in rows:
                if row.status == "blocked" and row.id in safe_ids:
                    row.status, row.error = "queued", None
            session.context_data = context
            await db.commit()
            return [input_item(row) for row in rows]

    async def recover(self, session_id, user_id):
        async with self.session_factory() as db:
            session = await self._lock(db, session_id, user_id)
            # Keep interruption detection and freezing under the same writer lock.
            started = await db.scalar(
                select(SessionInput.id)
                .where(
                    SessionInput.session_id == session_id,
                    SessionInput.status == "started",
                )
                .limit(1)
            )
            rows = (
                await self._freeze(
                    db,
                    session,
                    "Interrupted input has unknown effects; manual review required",
                )
                if started is not None
                else []
            )
            await db.commit()
            return [input_item(row) for row in rows]
