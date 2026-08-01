"""Recovery manager for agent session checkpoint recovery."""

from __future__ import annotations

from typing import Any

from app.core.checkpoint import SQLiteCheckpointStore


class RecoveryManager:
    """Manages recovery of agent sessions from checkpoints."""

    def __init__(self, checkpoint_store: SQLiteCheckpointStore | None = None):
        self._store = checkpoint_store or SQLiteCheckpointStore()

    async def recover_session(self, session_id: str) -> dict[str, Any] | None:
        """Recover a session from its latest checkpoint."""
        result = await self._store.get_latest(None, session_id)
        if not result:
            return None
        checkpoint, checkpoint_id = result
        return {
            "session_id": checkpoint.session_id,
            "turn_id": checkpoint.metadata.get("thread_id", ""),
            "messages": checkpoint.messages,
            "iteration": checkpoint.iteration,
            "status": checkpoint.status,
            "checkpoint_id": checkpoint_id,
        }

    async def list_recoverable_sessions(self) -> list[dict[str, Any]]:
        """List all sessions that have recoverable checkpoints."""
        from app.storage import async_session
        from app.storage.database import CheckpointRecord
        from sqlalchemy import func, select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord.session_id, func.count(CheckpointRecord.id))
                .group_by(CheckpointRecord.session_id)
            )
            rows = result.all()
            return [
                {"session_id": row[0], "checkpoint_count": row[1]}
                for row in rows
            ]

    async def auto_recover(self) -> list[dict[str, Any]]:
        """Auto-recover all sessions that have recoverable checkpoints."""
        from app.storage import async_session
        from app.storage.database import CheckpointRecord, Turn
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(
                select(CheckpointRecord.session_id)
                .distinct()
                .where(CheckpointRecord.status == "failed")
            )
            session_ids = [row[0] for row in result.all()]

            recovered = []
            for sid in session_ids:
                turn_result = await session.execute(
                    select(Turn)
                    .where(Turn.session_id == sid, Turn.status == "failed")
                )
                if turn_result.scalar_one_or_none():
                    checkpoint_result = await self._store.get_latest(None, sid)
                    if checkpoint_result:
                        checkpoint, cid = checkpoint_result
                        recovered.append({
                            "session_id": sid,
                            "status": "recovered",
                            "iteration": checkpoint.iteration,
                            "checkpoint_id": cid,
                        })
            return recovered
