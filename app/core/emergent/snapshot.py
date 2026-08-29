"""Structural snapshot & rollback for the fourth-generation modules.

Captures the mutable state that emergent modules can change — the
capability registry, graph definitions, and switch/config state — into a
JSON sidecar directory (`data/emergent_snapshots/`). Every structural
change is preceded by a snapshot (enforced by `HighRiskActionGuard`).
Rollback restores the captured state; the newest `keep_last` snapshots are
retained and older ones pruned.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class StructuralSnapshot:
    snapshot_id: str
    created_at: float
    path: str
    registry_payload: dict[str, Any]
    graph_payload: dict[str, Any]
    switches_payload: dict[str, Any]


class StructuralSnapshotManager:
    """Snapshot registry/graph/switches to JSON and restore on rollback."""

    def __init__(
        self,
        storage_dir: str = "data/emergent_snapshots",
        keep_last: int = 5,
        registry_dump: Callable[[], dict[str, Any]] | None = None,
        registry_restore: Callable[[dict[str, Any]], None] | None = None,
        graph_dump: Callable[[], dict[str, Any]] | None = None,
        graph_restore: Callable[[dict[str, Any]], None] | None = None,
        switches_dump: Callable[[], dict[str, Any]] | None = None,
        switches_restore: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.storage_dir = storage_dir
        self.keep_last = keep_last
        self.registry_dump = registry_dump or (lambda: {})
        self.registry_restore = registry_restore or (lambda payload: None)
        self.graph_dump = graph_dump or (lambda: {})
        self.graph_restore = graph_restore or (lambda payload: None)
        self.switches_dump = switches_dump or (lambda: {})
        self.switches_restore = switches_restore or (lambda payload: None)
        self._snapshots: dict[str, StructuralSnapshot] = {}
        self._seq = 0
        self._load_index()

    @property
    def _index_path(self) -> str:
        return os.path.join(self.storage_dir, "index.json")

    def _load_index(self) -> None:
        if not os.path.exists(self._index_path):
            return
        try:
            with open(self._index_path) as f:
                data = json.load(f)
            for sid, meta in data.items():
                self._snapshots[sid] = StructuralSnapshot(
                    snapshot_id=sid,
                    created_at=meta["created_at"],
                    path=meta["path"],
                    registry_payload={},
                    graph_payload={},
                    switches_payload={},
                )
        except (json.JSONDecodeError, KeyError, OSError):
            logger.warning("emergent_snapshot.index_corrupt")

    def _save_index(self) -> None:
        os.makedirs(self.storage_dir, exist_ok=True)
        data = {
            sid: {
                "created_at": snap.created_at,
                "path": snap.path,
            }
            for sid, snap in self._snapshots.items()
        }
        tmp = self._index_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self._index_path)

    async def capture(self, label: str = "") -> str:
        """Capture a full structural snapshot; returns the snapshot id.

        Raises when snapshotting fails so the hard guard aborts the change.
        """
        sid = f"snap_{int(time.time() * 1000)}_{self._seq}"
        self._seq += 1
        payload = {
            "id": sid,
            "label": label,
            "created_at": time.time(),
            "registry": self.registry_dump(),
            "graph": self.graph_dump(),
            "switches": self.switches_dump(),
        }
        os.makedirs(self.storage_dir, exist_ok=True)
        path = os.path.join(self.storage_dir, f"{sid}.json")
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)

        self._snapshots[sid] = StructuralSnapshot(
            snapshot_id=sid,
            created_at=payload["created_at"],
            path=path,
            registry_payload=payload["registry"],
            graph_payload=payload["graph"],
            switches_payload=payload["switches"],
        )
        self._prune()
        self._save_index()
        logger.info("emergent_snapshot.captured", snapshot_id=sid, label=label)
        return sid

    async def rollback(self, snapshot_id: str) -> bool:
        """Restore the state captured in the given snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap is None:
            return False
        if not os.path.exists(snap.path):
            return False
        try:
            with open(snap.path) as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False
        self.registry_restore(payload.get("registry", {}))
        self.graph_restore(payload.get("graph", {}))
        self.switches_restore(payload.get("switches", {}))
        logger.info("emergent_snapshot.rolled_back", snapshot_id=snapshot_id)
        return True

    def list_snapshots(self) -> list[dict[str, Any]]:
        return [
            {"snapshot_id": sid, "created_at": snap.created_at, "path": snap.path}
            for sid, snap in sorted(self._snapshots.items(), key=lambda kv: kv[1].created_at)
        ]

    def _prune(self) -> None:
        """Keep the newest `keep_last` snapshots; remove older files."""
        ordered = sorted(self._snapshots.items(), key=lambda kv: kv[1].created_at)
        drop = ordered[:max(0, len(ordered) - self.keep_last)]
        for sid, snap in drop:
            try:
                if os.path.exists(snap.path):
                    os.remove(snap.path)
            except OSError:
                pass
            self._snapshots.pop(sid, None)
            logger.info("emergent_snapshot.pruned", snapshot_id=sid)


# Process-wide defaults (noop dumps until wired in main).
_structural_snapshot_manager: StructuralSnapshotManager | None = None


def get_structural_snapshot_manager() -> StructuralSnapshotManager:
    global _structural_snapshot_manager
    if _structural_snapshot_manager is None:
        _structural_snapshot_manager = StructuralSnapshotManager()
    return _structural_snapshot_manager
