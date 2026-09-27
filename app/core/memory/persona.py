"""Agent persona/identity system.

Provides persistent agent persona storage and cross-session personality
inheritance. Persona is injected into system prompt as L0 layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import JSON, String, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.storage import Base, async_session

logger = structlog.get_logger()


@dataclass
class AgentPersona:
    """Agent persona defining identity, traits, and behavior.

    Injected into system prompt as L0 layer for consistent
    agent behavior across sessions.
    """

    agent_id: str
    name: str
    role: str = ""
    personality_traits: list[str] = field(default_factory=list)
    expertise: list[str] = field(default_factory=list)
    communication_style: str = ""
    goals: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_for_prompt(self) -> str:
        """Format persona for system prompt injection."""
        lines = [f"# Agent: {self.name}"]
        if self.role:
            lines.append(f"**Role:** {self.role}")
        if self.personality_traits:
            lines.append(f"**Traits:** {', '.join(self.personality_traits)}")
        if self.expertise:
            lines.append(f"**Expertise:** {', '.join(self.expertise)}")
        if self.communication_style:
            lines.append(f"**Communication Style:** {self.communication_style}")
        if self.goals:
            lines.append("**Goals:**")
            lines.extend(f"- {g}" for g in self.goals)
        return "\n".join(lines)


class PersonaModel(Base):
    """SQLAlchemy model for persistent persona storage."""

    __tablename__ = "personas"

    agent_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="")
    personality_traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    expertise: Mapped[list[str]] = mapped_column(JSON, default=list)
    communication_style: Mapped[str] = mapped_column(String(500), default="")
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(UTC).isoformat())
    updated_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(UTC).isoformat())


class SessionPersonaModel(Base):
    """SQLAlchemy model for session-specific persona overrides."""

    __tablename__ = "session_personas"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    base_persona_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    learnings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now(UTC).isoformat())


class PersonaStore:
    """CRUD operations for agent personas stored in SQLite."""

    async def save(self, persona: AgentPersona) -> AgentPersona:
        """Save or update a persona."""
        now = datetime.now(UTC).isoformat()
        persona.updated_at = now
        async with async_session() as db:
            existing = await db.get(PersonaModel, persona.agent_id)
            if existing:
                existing.name = persona.name
                existing.role = persona.role
                existing.personality_traits = persona.personality_traits
                existing.expertise = persona.expertise
                existing.communication_style = persona.communication_style
                existing.goals = persona.goals
                existing.updated_at = now
            else:
                db.add(PersonaModel(
                    agent_id=persona.agent_id,
                    name=persona.name,
                    role=persona.role,
                    personality_traits=persona.personality_traits,
                    expertise=persona.expertise,
                    communication_style=persona.communication_style,
                    goals=persona.goals,
                    created_at=persona.created_at,
                    updated_at=now,
                ))
            await db.commit()
        logger.info("persona_saved", agent_id=persona.agent_id)
        return persona

    async def load(self, agent_id: str) -> AgentPersona | None:
        """Load a persona by agent_id."""
        async with async_session() as db:
            model = await db.get(PersonaModel, agent_id)
            if not model:
                return None
            return AgentPersona(
                agent_id=model.agent_id,
                name=model.name,
                role=model.role,
                personality_traits=model.personality_traits or [],
                expertise=model.expertise or [],
                communication_style=model.communication_style or "",
                goals=model.goals or [],
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    async def update(self, agent_id: str, **kwargs: Any) -> AgentPersona | None:
        """Update specific fields of a persona."""
        async with async_session() as db:
            model = await db.get(PersonaModel, agent_id)
            if not model:
                return None
            for key, value in kwargs.items():
                if hasattr(model, key) and value is not None:
                    setattr(model, key, value)
            model.updated_at = datetime.now(UTC).isoformat()
            await db.commit()
            return await self.load(agent_id)

    async def delete(self, agent_id: str) -> bool:
        """Delete a persona."""
        async with async_session() as db:
            result = await db.execute(
                delete(PersonaModel).where(PersonaModel.agent_id == agent_id)
            )
            await db.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info("persona_deleted", agent_id=agent_id)
            return deleted

    async def list_all(self) -> list[AgentPersona]:
        """List all stored personas."""
        async with async_session() as db:
            result = await db.execute(select(PersonaModel))
            models = result.scalars().all()
            return [
                AgentPersona(
                    agent_id=m.agent_id,
                    name=m.name,
                    role=m.role,
                    personality_traits=m.personality_traits or [],
                    expertise=m.expertise or [],
                    communication_style=m.communication_style or "",
                    goals=m.goals or [],
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in models
            ]


def create_session_persona(
    session_id: str,
    base_persona_id: str,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a session-specific persona configuration.

    Returns a dict representing the session persona with overrides applied.
    """
    return {
        "session_id": session_id,
        "base_persona_id": base_persona_id,
        "overrides": overrides or {},
        "learnings": {},
        "created_at": datetime.now(UTC).isoformat(),
    }


async def merge_session_persona(session_id: str) -> dict[str, Any] | None:
    """Merge session learnings back into the base persona.

    Returns the merge report with what was updated.
    """
    async with async_session() as db:
        model = await db.get(SessionPersonaModel, session_id)
        if not model:
            return None

        store = PersonaStore()
        base_persona = await store.load(model.base_persona_id)
        if not base_persona:
            return None

        report: dict[str, Any] = {
            "session_id": session_id,
            "base_persona_id": model.base_persona_id,
            "merged_fields": [],
        }

        learnings = model.learnings or {}
        if "new_expertise" in learnings:
            existing = set(base_persona.expertise)
            for item in learnings["new_expertise"]:
                if item not in existing:
                    base_persona.expertise.append(item)
            report["merged_fields"].append("expertise")

        if "goal_progress" in learnings:
            existing_goals = set(base_persona.goals)
            for item in learnings["goal_progress"]:
                if item not in existing_goals:
                    base_persona.goals.append(item)
            report["merged_fields"].append("goals")

        if "style_feedback" in learnings:
            base_persona.communication_style = learnings["style_feedback"]
            report["merged_fields"].append("communication_style")

        await store.save(base_persona)
        logger.info("session_persona_merged", **report)
        return report


async def get_effective_persona(
    session_id: str | None,
    agent_id: str,
) -> AgentPersona | None:
    """Get the effective persona with inheritance resolved.

    If session_id is provided, applies session-specific overrides
    on top of the base persona.
    """
    store = PersonaStore()
    base = await store.load(agent_id)
    if not base or not session_id:
        return base

    async with async_session() as db:
        session_model = await db.get(SessionPersonaModel, session_id)
        if not session_model:
            return base

        overrides = session_model.overrides or {}
        if overrides:
            return AgentPersona(
                agent_id=base.agent_id,
                name=overrides.get("name", base.name),
                role=overrides.get("role", base.role),
                personality_traits=overrides.get("personality_traits", base.personality_traits),
                expertise=overrides.get("expertise", base.expertise),
                communication_style=overrides.get("communication_style", base.communication_style),
                goals=overrides.get("goals", base.goals),
                created_at=base.created_at,
                updated_at=base.updated_at,
            )
        return base


# Global singleton
persona_store = PersonaStore()
