"""Checkpoint store with ancestor traversal.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.pregel_loop import Checkpoint, PendingWrite

logger = logging.getLogger(__name__)


class CheckpointStore:
    """Persistent checkpoint storage with ancestor traversal."""

    def __init__(self):
        self._checkpoints: dict[str, list[Checkpoint]] = {}

    async def put(self, thread_id: str, checkpoint: Checkpoint) -> None:
        if thread_id not in self._checkpoints:
            self._checkpoints[thread_id] = []
        self._checkpoints[thread_id].append(checkpoint)
        logger.debug("checkpoint_saved", thread_id=thread_id, step=checkpoint.step)

    async def get(self, thread_id: str, step: int | None = None) -> Checkpoint | None:
        checkpoints = self._checkpoints.get(thread_id, [])
        if not checkpoints:
            return None
        if step is None:
            return checkpoints[-1]
        for cp in reversed(checkpoints):
            if cp.step == step:
                return cp
        return None

    async def get_latest(self, thread_id: str) -> Checkpoint | None:
        return await self.get(thread_id)

    async def list(self, thread_id: str) -> list[dict[str, Any]]:
        checkpoints = self._checkpoints.get(thread_id, [])
        return [
            {"step": cp.step, "metadata": cp.metadata}
            for cp in checkpoints
        ]

    async def delete(self, thread_id: str, step: int | None = None) -> bool:
        if thread_id not in self._checkpoints:
            return False
        if step is None:
            del self._checkpoints[thread_id]
            return True
        self._checkpoints[thread_id] = [cp for cp in self._checkpoints[thread_id] if cp.step != step]
        return True

    async def ancestor_walk(self, thread_id: str, target_step: int) -> Checkpoint | None:
        """Ancestor walk: find the checkpoint at or before target_step."""
        checkpoints = self._checkpoints.get(thread_id, [])
        candidate = None
        for cp in checkpoints:
            if cp.step <= target_step:
                candidate = cp
            else:
                break
        return candidate

    async def replay_pending_writes(self, thread_id: str, target_step: int) -> list[PendingWrite]:
        """Replay pending writes from ancestor checkpoint to target_step."""
        ancestor = await self.ancestor_walk(thread_id, target_step)
        if not ancestor:
            return []
        return [pw for pw in ancestor.pending_writes if pw.status == "pending"]
