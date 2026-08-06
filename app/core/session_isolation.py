"""Session isolation sandbox.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionWorkspace:
    session_id: str
    root_path: str
    env_vars: dict[str, str] = field(default_factory=dict)
    working_dir: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionIsolationSandbox:
    """Isolate each session into its own workspace.

    """

    def __init__(self, base_dir: str = "./data/sessions"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, SessionWorkspace] = {}

    def create_workspace(self, session_id: str) -> SessionWorkspace:
        session_dir = self._base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        workspace = SessionWorkspace(
            session_id=session_id,
            root_path=str(session_dir),
            working_dir=str(session_dir),
        )
        self._workspaces[session_id] = workspace
        logger.info("session_workspace_created", session_id=session_id, path=str(session_dir))
        return workspace

    def get_workspace(self, session_id: str) -> SessionWorkspace | None:
        return self._workspaces.get(session_id)

    def remove_workspace(self, session_id: str) -> bool:
        if session_id in self._workspaces:
            del self._workspaces[session_id]
            return True
        return False

    def isolate_path(self, session_id: str, target_path: str) -> str:
        workspace = self._workspaces.get(session_id)
        if not workspace:
            raise ValueError(f"Session workspace not found: {session_id}")
        target = Path(target_path)
        if not target.is_absolute():
            target = Path(workspace.working_dir) / target
        try:
            target.relative_to(Path(workspace.root_path))
        except ValueError:
            raise PermissionError(f"Path escapes session workspace: {target_path}")
        return str(target)

    def list_files(self, session_id: str) -> list[str]:
        workspace = self._workspaces.get(session_id)
        if not workspace:
            return []
        root = Path(workspace.root_path)
        return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]

    def cleanup(self, session_id: str) -> None:
        import shutil
        workspace = self._workspaces.get(session_id)
        if workspace and Path(workspace.root_path).exists():
            shutil.rmtree(workspace.root_path, ignore_errors=True)
            self._workspaces.pop(session_id, None)


session_isolation = SessionIsolationSandbox()
