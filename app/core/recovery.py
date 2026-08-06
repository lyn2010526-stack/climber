"""Recovery manager for agent session checkpoint recovery."""

from __future__ import annotations

from typing import Any

from app.core.checkpoint import CheckpointData, SQLiteCheckpointStore
from app.core.session import AgentSession


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
        interrupted = self._is_interrupted(checkpoint)
        return {
            "session_id": checkpoint.session_id,
            "turn_id": checkpoint.metadata.get("thread_id", ""),
            "messages": checkpoint.messages,
            "iteration": checkpoint.iteration,
            "status": checkpoint.status,
            "tool_results": checkpoint.tool_results,
            "channel_values": checkpoint.channel_values,
            "channel_versions": checkpoint.channel_versions,
            "versions_seen": checkpoint.versions_seen,
            "pending_writes": checkpoint.pending_writes,
            "interrupted": interrupted,
            "checkpoint_id": checkpoint_id,
            "checkpoint": checkpoint,
        }

    async def restore_session(self, session: AgentSession) -> bool:
        """Restore checkpoint state into an existing canonical session."""
        recovered = await self.recover_session(session.session_id)
        if recovered is None:
            return False
        session.restore_checkpoint(
            recovered["checkpoint"],
            interrupted=recovered["interrupted"],
        )
        return True

    @staticmethod
    def _is_interrupted(checkpoint: CheckpointData) -> bool:
        if checkpoint.status not in {"running", "processing", "retrying"}:
            return False
        final_keys = {"final_content", "final_result"}
        return final_keys.isdisjoint(checkpoint.channel_values)

    async def list_recoverable_sessions(self) -> list[dict[str, Any]]:
        """List all sessions that have recoverable checkpoints."""
        from sqlalchemy import func, select

        from app.storage import async_session
        from app.storage.database import CheckpointRecord

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
        from sqlalchemy import select

        from app.storage import async_session
        from app.storage.database import CheckpointRecord, Turn

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
