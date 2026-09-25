"""Recovery manager for agent session checkpoint recovery."""

from __future__ import annotations

from typing import Any

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.session import AgentSession


class RecoveryManager:
    """Manages recovery of agent sessions from checkpoints."""

    def __init__(self, checkpoint_store: SQLiteCheckpointStore | InMemoryCheckpointStore | None = None):
        self._store = checkpoint_store if checkpoint_store is not None else SQLiteCheckpointStore()

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
        if recovered["pending_writes"]:
            raise ValueError("Checkpoint has pending writes; automatic replay is unsafe")
        session.restore_checkpoint(
            recovered["checkpoint"],
            interrupted=recovered["interrupted"],
        )
        session._last_checkpoint_id = recovered["checkpoint_id"]
        if not recovered["interrupted"] and recovered["status"] in {"failed", "cancelled", "stopped"}:
            session._restore_status(recovered["status"])
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
        """Discover resumable state; this does not run a model or replay tools."""
        candidates = []
        for item in await self.list_recoverable_sessions():
            recovered = await self.recover_session(item["session_id"])
            if recovered and recovered["interrupted"] and not recovered["pending_writes"]:
                candidates.append({
                    "session_id": recovered["session_id"], "status": "recoverable",
                    "iteration": recovered["iteration"],
                    "checkpoint_id": recovered["checkpoint_id"],
                })
        return candidates
