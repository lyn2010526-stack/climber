"""Recovery manager for agent session checkpoint recovery."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from app.core.checkpoint import CheckpointData, InMemoryCheckpointStore, SQLiteCheckpointStore
from app.core.replay import ToolReplayPolicy

if TYPE_CHECKING:
    from app.core.session import AgentSession


class RecoveryManager:
    """Manages recovery of agent sessions from checkpoints."""

    def __init__(self, checkpoint_store: InMemoryCheckpointStore | SQLiteCheckpointStore | None = None):
        self._store = checkpoint_store or SQLiteCheckpointStore()
        self._replay_policy = ToolReplayPolicy()

    async def recover_session(self, session_id: str) -> dict[str, Any] | None:
        """Recover a session from its latest checkpoint.

        Recorded ``tool_results`` are split by the replay policy: results from
        read-only tools can be handed back to the model, while results from
        writes, commands and network calls are withheld, because replaying them
        would repeat a side effect the checkpoint cannot vouch for.
        """
        result = await self._store.get_latest(None, session_id)
        if not result:
            return None
        checkpoint, checkpoint_id = result
        interrupted = self._is_interrupted(checkpoint)
        recorded = list(checkpoint.tool_results or [])
        replayable = self._replay_policy.filter(recorded)
        replayed_ids = {id(entry) for entry in replayable}
        withheld = [entry for entry in recorded if id(entry) not in replayed_ids]
        messages = self._messages_with_replayed_results(
            checkpoint.messages, replayable, withheld
        )
        return {
            "session_id": checkpoint.session_id,
            "turn_id": checkpoint.metadata.get("thread_id", ""),
            "messages": messages,
            "iteration": checkpoint.iteration,
            "status": checkpoint.status,
            "tool_results": replayable,
            "withheld_tool_results": withheld,
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
        session.messages = copy.deepcopy(recovered["messages"])
        session.tool_results = copy.deepcopy(recovered["tool_results"])
        session._last_checkpoint_id = recovered["checkpoint_id"]
        if not recovered["interrupted"] and recovered["status"] in {"failed", "cancelled", "stopped"}:
            session._restore_status(recovered["status"])
        return True

    async def rollback_session(
        self,
        session_id: str,
        checkpoint_id: str,
        prune_descendants: bool = True,
    ) -> dict[str, Any] | None:
        """Roll a session back to a specific checkpoint in the engine store.

        Mirrors :meth:`recover_session` but targets an arbitrary ancestor
        instead of the latest checkpoint. With ``prune_descendants`` the store
        drops every checkpoint that descends from the target, so subsequent
        saves continue the timeline from the rollback point. Returns the same
        payload shape as ``recover_session``, or ``None`` when the checkpoint
        does not exist or belongs to a different session.
        """
        target = await self._store.rollback_to(checkpoint_id, prune_descendants=prune_descendants)
        if target is None or target.session_id != session_id:
            return None
        recorded = list(target.tool_results or [])
        replayable = self._replay_policy.filter(recorded)
        replayed_ids = {id(entry) for entry in replayable}
        withheld = [entry for entry in recorded if id(entry) not in replayed_ids]
        return {
            "session_id": target.session_id,
            "turn_id": target.metadata.get("thread_id", ""),
            "messages": self._messages_with_replayed_results(
                target.messages, replayable, withheld
            ),
            "iteration": target.iteration,
            "status": target.status,
            "tool_results": replayable,
            "withheld_tool_results": withheld,
            "channel_values": target.channel_values,
            "channel_versions": target.channel_versions,
            "versions_seen": target.versions_seen,
            "pending_writes": target.pending_writes,
            "interrupted": self._is_interrupted(target),
            "checkpoint_id": checkpoint_id,
            "checkpoint": target,
        }

    async def rollback_and_restore(
        self,
        session: AgentSession,
        checkpoint_id: str,
        prune_descendants: bool = True,
    ) -> bool:
        """Roll the store back to ``checkpoint_id`` and load it into ``session``."""
        rolled = await self.rollback_session(
            session.session_id, checkpoint_id, prune_descendants=prune_descendants
        )
        if rolled is None:
            return False
        session.restore_checkpoint(
            rolled["checkpoint"],
            interrupted=rolled["interrupted"],
        )
        session.messages = copy.deepcopy(rolled["messages"])
        session.tool_results = copy.deepcopy(rolled["tool_results"])
        return True

    @staticmethod
    def _is_interrupted(checkpoint: CheckpointData) -> bool:
        if checkpoint.status not in {"running", "processing", "retrying"}:
            return False
        final_keys = {"final_content", "final_result"}
        return final_keys.isdisjoint(checkpoint.channel_values)

    @staticmethod
    def _messages_with_replayed_results(
        messages: list[dict[str, Any]],
        replayable: list[dict[str, Any]],
        withheld: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Append safe recorded results as model-visible tool messages."""
        withheld_ids = {
            entry.get("tool_call_id") or entry.get("id")
            for entry in withheld
            if isinstance(entry, dict)
        }
        restored = [
            copy.deepcopy(message)
            for message in messages
            if not (
                isinstance(message, dict)
                and message.get("role") == "tool"
                and message.get("tool_call_id") in withheld_ids
            )
        ]
        existing_ids = {
            message.get("tool_call_id")
            for message in restored
            if isinstance(message, dict) and message.get("role") == "tool"
        }
        for index, entry in enumerate(replayable):
            if not isinstance(entry, dict):
                continue
            tool_name = entry.get("tool") or entry.get("tool_name")
            if not isinstance(tool_name, str) or not tool_name:
                continue
            call_id = entry.get("tool_call_id") or entry.get("id") or f"replay-{tool_name}-{index}"
            if call_id in existing_ids:
                continue
            content = entry.get("result", entry.get("output", ""))
            if entry.get("error") or entry.get("success") is False:
                content = f"Tool execution failed: {entry.get('error') or 'recorded failure'}"
                if entry.get("result"):
                    content += f"\n\nTool output:\n{entry['result']}"
            restored.append({
                "role": "tool",
                "content": content,
                "tool_call_id": str(call_id),
            })
            existing_ids.add(call_id)
        return restored

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
