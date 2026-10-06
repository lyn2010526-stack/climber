"""Model-independent task views over durable records, ready for engine hooks.

Call restore before prompt construction and summarize_turn after RunStorage.finish
under the existing session execution lock. Summaries are derived observations;
completed execution carries no implied business acceptance.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select, update

from app.storage.database import Session, SessionInput, Turn
from app.storage.models_instruction_traces import InstructionTrace


class TaskMemory:
    """Inject the production async session factory, or a private test factory."""

    def __init__(self, session_factory: Any):
        self.session_factory = session_factory

    async def _owner(self, db: Any, session_id: str, user_id: str) -> None:
        if (
            not session_id
            or not user_id
            or await db.scalar(
                select(Session.id).where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                )
            )
            is None
        ):
            raise LookupError("Session not found")

    @staticmethod
    def _item(source: str, row: Any, text: str, status: str, **details: Any) -> dict:
        return {
            "source_id": f"{source}:{row.id}",
            "text": text,
            "status": status,
            "acceptance": "unverified",
            **details,
        }

    async def _layers(
        self, db: Any, session_id: str, user_id: str, turn_id: str | None = None
    ) -> dict:
        traces_query = (
            select(InstructionTrace)
            .where(
                InstructionTrace.session_id == session_id,
                InstructionTrace.user_id == user_id,
            )
            .order_by(InstructionTrace.created_at, InstructionTrace.id)
        )
        turns_query = (
            select(Turn).where(Turn.session_id == session_id).order_by(Turn.created_at, Turn.id)
        )
        if turn_id is not None:
            traces_query = traces_query.where(InstructionTrace.turn_id == turn_id)
            turns_query = turns_query.where(Turn.id == turn_id)
        traces = (await db.scalars(traces_query)).all()
        turns = (await db.scalars(turns_query)).all()
        summary_ids = set(
            (
                await db.scalars(
                    select(InstructionTrace.compressed_into_id).where(
                        InstructionTrace.session_id == session_id,
                        InstructionTrace.user_id == user_id,
                        InstructionTrace.compressed_into_id.is_not(None),
                    )
                )
            ).all()
        )
        by_turn = {row.id: row for row in turns}
        layers: dict[str, list] = {"planning": [], "completed": [], "todo": []}
        for trace in traces:
            # Compression creates derived trace rows; retain original instructions only.
            if trace.id in summary_ids:
                continue
            turn = by_turn.get(trace.turn_id)
            outcome = (turn.metadata_ or {}).get("outcome") if turn else trace.outcome
            status = turn.status if turn else trace.status
            item = self._item(
                "instruction",
                trace,
                trace.raw_text,
                status,
                task_spec=trace.task_spec,
                outcome=outcome,
                turn_source_id=f"turn:{turn.id}" if turn else None,
            )
            layers["planning"].append(item)
            done = status == "completed" and outcome in (None, "completed", "success")
            layers["completed" if done else "todo"].append(item)
        for turn in turns:
            outcome = (turn.metadata_ or {}).get("outcome")
            done = turn.status == "completed" and outcome in (None, "completed", "success")
            layers["completed" if done else "todo"].append(
                self._item(
                    "turn",
                    turn,
                    turn.result or turn.error or "",
                    turn.status,
                    outcome=outcome,
                    error=turn.error,
                    checkpoint_id=turn.checkpoint_id,
                )
            )
        # SessionInput has no turn foreign key. Never guess a turn from message text.
        if turn_id is None:
            inputs = (
                await db.scalars(
                    select(SessionInput)
                    .where(
                        SessionInput.session_id == session_id,
                    )
                    .order_by(SessionInput.sequence, SessionInput.id)
                )
            ).all()
            for row in inputs:
                item = self._item(
                    "input",
                    row,
                    row.message,
                    row.status,
                    kind=row.kind,
                    sequence=row.sequence,
                    error=row.error,
                )
                layers["planning"].append(item)
                layers["completed" if row.status == "completed" else "todo"].append(item)
        return layers

    async def restore(self, session_id: str, user_id: str, *, token_budget: int = 2048) -> dict:
        """Return complete layers plus a bounded context, independently of model.

        UTF-8 byte length is a conservative text-token upper bound. Whole JSON
        records are selected with todo first; omitted records remain in layers.
        The caller reserves provider framing/tool overhead separately.
        """
        if isinstance(token_budget, bool) or not isinstance(token_budget, int) or token_budget < 0:
            raise ValueError("token_budget must be a nonnegative integer")
        async with self.session_factory() as db:
            await self._owner(db, session_id, user_id)
            layers = await self._layers(db, session_id, user_id)
        lines, used = [], 0
        omitted = dict.fromkeys(layers, 0)
        for name in ("todo", "planning", "completed"):
            for item in layers[name]:
                line = json.dumps({"layer": name, **item}, ensure_ascii=False, sort_keys=True)
                cost = len((line + "\n").encode("utf-8"))
                if used + cost <= token_budget:
                    lines.append(line + "\n")
                    used += cost
                else:
                    omitted[name] += 1
        return {
            "session_id": session_id,
            "layers": layers,
            "task_context": "".join(lines),
            "budget_used": used,
            "omitted": omitted,
        }

    async def task_context(self, session_id: str, user_id: str, *, token_budget: int = 2048) -> str:
        """Prompt hook convenience entry point; use restore for omission diagnostics."""
        return (await self.restore(session_id, user_id, token_budget=token_budget))["task_context"]

    async def summarize_turn(self, session_id: str, user_id: str, turn_id: str) -> dict:
        """Idempotently store a lossless structured recap in Turn.metadata_.

        Serializes this module's writers via the owned session row. Mainline
        callers should finish run bookkeeping first and retain the session lock.
        """
        async with self.session_factory() as db:
            locked = await db.execute(
                update(Session)
                .where(
                    Session.id == session_id,
                    Session.user_id == user_id,
                )
                .values(updated_at=Session.updated_at)
            )
            if not session_id or not user_id or locked.rowcount != 1:
                raise LookupError("Session not found")
            turn = await db.scalar(
                select(Turn).where(Turn.id == turn_id, Turn.session_id == session_id)
            )
            if turn is None:
                raise LookupError("Turn not found")
            layers = await self._layers(db, session_id, user_id, turn_id)
            payload = {"schema_version": 1, "turn_source_id": f"turn:{turn.id}", "layers": layers}
            digest = hashlib.sha256(
                json.dumps(
                    payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            metadata = dict(turn.metadata_ or {})
            previous = metadata.get("task_memory")
            if isinstance(previous, dict) and previous.get("source_hash") == digest:
                await db.commit()
                return previous
            summary = {
                **payload,
                "source_hash": digest,
                "revision": (previous.get("revision", 0) if isinstance(previous, dict) else 0) + 1,
            }
            turn.metadata_ = {**metadata, "task_memory": summary}
            await db.commit()
            return summary
