"""Working Memory (L1) — structured per-session context.

Slots:
- goals: list[str]       — current task objectives
- observations: list[str] — facts gathered during execution
- hypotheses: list[str]   — candidate explanations or plans
- constraints: list[str]  — boundaries and requirements
- progress: list[str]     — completed step log

Stored as JSON in the sessions table via a dedicated column.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from sqlalchemy import select

logger = logging.getLogger(__name__)

WORKING_MEMORY_SLOTS = ("goals", "observations", "hypotheses", "constraints", "progress")


@dataclass
class WorkingMemoryState:
    goals: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    progress: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(self, raw: str | None) -> WorkingMemoryState:
        if not raw:
            return WorkingMemoryState()
        try:
            data = json.loads(raw)
            return WorkingMemoryState(**{k: data.get(k, []) for k in WORKING_MEMORY_SLOTS})
        except (json.JSONDecodeError, TypeError):
            return WorkingMemoryState()

    def format_for_prompt(self) -> str:
        """Format working memory for system prompt injection."""
        parts: list[str] = []
        if self.goals:
            parts.append("## Current Goals")
            parts.extend(f"- {g}" for g in self.goals)
        if self.observations:
            parts.append("## Observations")
            parts.extend(f"- {o}" for o in self.observations)
        if self.hypotheses:
            parts.append("## Hypotheses")
            parts.extend(f"- {h}" for h in self.hypotheses)
        if self.constraints:
            parts.append("## Constraints")
            parts.extend(f"- {c}" for c in self.constraints)
        if self.progress:
            parts.append("## Progress Log")
            parts.extend(f"- {p}" for p in self.progress)
        return "\n".join(parts)

    def add(self, slot: str, content: str) -> None:
        if slot in WORKING_MEMORY_SLOTS:
            getattr(self, slot).append(content)


class WorkingMemoryService:
    """Manage working memory persistence via the sessions table."""

    async def get_state(self, session_id: str) -> WorkingMemoryState:
        from app.storage import async_session
        from app.storage.database import Session as SessionModel

        async with async_session() as db:
            result = await db.execute(
                select(SessionModel.working_memory).where(
                    SessionModel.id == session_id
                )
            )
            raw = result.scalar_one_or_none()
            return WorkingMemoryState.from_json(raw)

    async def save_state(self, session_id: str, state: WorkingMemoryState) -> None:
        from app.storage import async_session
        from app.storage.database import Session as SessionModel

        async with async_session() as db:
            session = await db.get(SessionModel, session_id)
            if session is not None:
                session.working_memory = state.to_json()
                await db.commit()

    async def add_entry(self, session_id: str, slot: str, content: str) -> WorkingMemoryState:
        state = await self.get_state(session_id)
        state.add(slot, content)
        await self.save_state(session_id, state)
        return state

    async def clear(self, session_id: str) -> None:
        await self.save_state(session_id, WorkingMemoryState())


_working_memory_default: WorkingMemoryService | None = None


def get_working_memory() -> WorkingMemoryService:
    global _working_memory_default
    if _working_memory_default is None:
        _working_memory_default = WorkingMemoryService()
    return _working_memory_default


def __getattr__(name: str):
    if name == "working_memory_service":
        return get_working_memory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



