"""Session manager — handles agent sessions."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SessionInfo:
    session_id: str
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages agent sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionInfo] = {}

    def create(self, user_id: str = "", **kwargs: Any) -> SessionInfo:
        session_id = str(uuid.uuid4())[:12]
        info = SessionInfo(session_id=session_id, user_id=user_id, metadata=kwargs)
        self._sessions[session_id] = info
        return info

    def get(self, session_id: str) -> SessionInfo | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def list_all(self) -> list[SessionInfo]:
        return list(self._sessions.values())
