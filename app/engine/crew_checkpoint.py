"""Crew execution checkpoint with resume capability.

Allows saving and restoring crew execution state for fault tolerance
and long-running task support.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class CrewCheckpoint(BaseModel):
    """Crew execution checkpoint.

    Captures the state of a crew execution at a specific point,
    allowing resumption from where it left off.
    """

    crew_id: str
    task_index: int
    results: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])


class CheckpointManager:
    """Manage crew execution checkpoints.

    Supports saving, loading, and resuming crew executions.
    Checkpoints can be stored in-memory or persisted to disk.
    """

    def __init__(self, persist_dir: str | None = None):
        self._checkpoints: dict[str, CrewCheckpoint] = {}
        self._persist_dir: Path | None = Path(persist_dir) if persist_dir else None

        if self._persist_dir:
            self._persist_dir.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        crew_id: str,
        task_index: int,
        results: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> CrewCheckpoint:
        """Save a checkpoint for a crew execution."""
        checkpoint = CrewCheckpoint(
            crew_id=crew_id,
            task_index=task_index,
            results=results,
            metadata=metadata or {},
        )

        key = self._make_key(crew_id, task_index)
        self._checkpoints[key] = checkpoint

        if self._persist_dir:
            await self._persist_checkpoint(checkpoint)

        logger.info(
            "checkpoint_saved",
            crew_id=crew_id,
            task_index=task_index,
            checkpoint_id=checkpoint.checkpoint_id,
        )
        return checkpoint

    async def load(self, crew_id: str) -> CrewCheckpoint | None:
        """Load the latest checkpoint for a crew."""
        latest: CrewCheckpoint | None = None

        for key, cp in self._checkpoints.items():
            if cp.crew_id == crew_id:
                if latest is None or cp.task_index > latest.task_index:
                    latest = cp

        if latest is None and self._persist_dir:
            latest = await self._load_latest_from_disk(crew_id)

        if latest:
            logger.info(
                "checkpoint_loaded",
                crew_id=crew_id,
                task_index=latest.task_index,
                checkpoint_id=latest.checkpoint_id,
            )
        else:
            logger.info("checkpoint_not_found", crew_id=crew_id)

        return latest

    async def load_specific(self, checkpoint_id: str) -> CrewCheckpoint | None:
        """Load a specific checkpoint by ID."""
        for cp in self._checkpoints.values():
            if cp.checkpoint_id == checkpoint_id:
                return cp

        if self._persist_dir:
            return await self._load_from_disk(checkpoint_id)

        return None

    async def resume(
        self,
        crew_id: str,
        crew_factory: Any = None,
    ) -> Any | None:
        """Resume a crew execution from its latest checkpoint.

        If a crew_factory is provided, creates a new crew instance
        with the checkpoint's state and continues execution.
        Returns the checkpoint if found, None otherwise.
        """
        checkpoint = await self.load(crew_id)
        if not checkpoint:
            logger.warning("resume_no_checkpoint", crew_id=crew_id)
            return None

        logger.info(
            "crew_resuming",
            crew_id=crew_id,
            task_index=checkpoint.task_index,
            results_count=len(checkpoint.results),
        )

        if crew_factory:
            crew = crew_factory(
                task_index=checkpoint.task_index,
                previous_results=checkpoint.results,
            )
            return crew

        return checkpoint

    async def list_checkpoints(self, crew_id: str | None = None) -> list[CrewCheckpoint]:
        """List all checkpoints, optionally filtered by crew_id."""
        checkpoints = list(self._checkpoints.values())

        if crew_id:
            checkpoints = [cp for cp in checkpoints if cp.crew_id == crew_id]

        if self._persist_dir:
            disk_checkpoints = await self._list_disk_checkpoints(crew_id)
            existing_ids = {cp.checkpoint_id for cp in checkpoints}
            checkpoints.extend(
                cp for cp in disk_checkpoints if cp.checkpoint_id not in existing_ids
            )

        checkpoints.sort(key=lambda cp: cp.created_at, reverse=True)
        return checkpoints

    async def delete(self, crew_id: str) -> int:
        """Delete all checkpoints for a crew."""
        to_delete = [
            key for key, cp in self._checkpoints.items() if cp.crew_id == crew_id
        ]
        for key in to_delete:
            del self._checkpoints[key]

        if self._persist_dir:
            await self._delete_persisted(crew_id)

        logger.info("checkpoints_deleted", crew_id=crew_id, count=len(to_delete))
        return len(to_delete)

    def _make_key(self, crew_id: str, task_index: int) -> str:
        """Generate a storage key for a checkpoint."""
        return f"{crew_id}:{task_index}"

    async def _persist_checkpoint(self, checkpoint: CrewCheckpoint) -> None:
        """Persist a checkpoint to disk."""
        if not self._persist_dir:
            return

        try:
            filename = f"{checkpoint.crew_id}_{checkpoint.checkpoint_id}.json"
            filepath = self._persist_dir / filename
            data = checkpoint.model_dump()
            data["created_at"] = data["created_at"].isoformat()

            loop = __import__("asyncio").get_event_loop()
            await loop.run_in_executor(
                None, lambda: filepath.write_text(json.dumps(data, indent=2, default=str)),
            )
        except Exception as e:
            logger.error("checkpoint_persist_failed", error=str(e))

    async def _load_latest_from_disk(self, crew_id: str) -> CrewCheckpoint | None:
        """Load the latest checkpoint from disk."""
        if not self._persist_dir:
            return None

        try:
            loop = __import__("asyncio").get_event_loop()
            files = await loop.run_in_executor(
                None,
                lambda: list(self._persist_dir.glob(f"{crew_id}_*.json")),
            )

            if not files:
                return None

            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            data = json.loads(latest_file.read_text())
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            return CrewCheckpoint(**data)
        except Exception as e:
            logger.error("checkpoint_load_failed", error=str(e))
            return None

    async def _load_from_disk(self, checkpoint_id: str) -> CrewCheckpoint | None:
        """Load a specific checkpoint from disk by ID."""
        if not self._persist_dir:
            return None

        try:
            loop = __import__("asyncio").get_event_loop()
            files = await loop.run_in_executor(
                None,
                lambda: list(self._persist_dir.glob(f"*_{checkpoint_id}.json")),
            )

            if not files:
                return None

            data = json.loads(files[0].read_text())
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            return CrewCheckpoint(**data)
        except Exception as e:
            logger.error("checkpoint_load_failed", error=str(e))
            return None

    async def _list_disk_checkpoints(
        self, crew_id: str | None = None,
    ) -> list[CrewCheckpoint]:
        """List checkpoints from disk."""
        if not self._persist_dir:
            return []

        try:
            loop = __import__("asyncio").get_event_loop()
            pattern = f"{crew_id}_*.json" if crew_id else "*.json"
            files = await loop.run_in_executor(
                None,
                lambda: list(self._persist_dir.glob(pattern)),
            )

            checkpoints: list[CrewCheckpoint] = []
            for f in files:
                try:
                    data = json.loads(f.read_text())
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                    checkpoints.append(CrewCheckpoint(**data))
                except Exception:
                    continue

            return checkpoints
        except Exception:
            return []

    async def _delete_persisted(self, crew_id: str) -> None:
        """Delete persisted checkpoint files for a crew."""
        if not self._persist_dir:
            return

        try:
            loop = __import__("asyncio").get_event_loop()
            files = await loop.run_in_executor(
                None,
                lambda: list(self._persist_dir.glob(f"{crew_id}_*.json")),
            )
            for f in files:
                f.unlink(missing_ok=True)
        except Exception as e:
            logger.error("checkpoint_delete_failed", error=str(e))
