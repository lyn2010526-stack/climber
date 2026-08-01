"""Agent Identity — Persistent agent with its own memory scope.

Provides a persistent agent abstraction that maintains its own
identity, goals, and memory scope across sessions. Each agent
has a dedicated MemFS instance for its memory files.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class AgentSession:
    """Represents an active session for an agent."""

    session_id: str
    agent_id: str
    user_id: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    message_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "message_count": self.message_count,
            "is_active": self.is_active,
        }


class AgentIdentity:
    """Persistent agent with its own memory scope.

    Each agent has:
    - A unique identity (name, persona, goals)
    - Its own MemFS memory scope
    - Session management capabilities
    - Memory recall and storage methods

    Args:
        agent_id: Unique identifier for the agent.
        name: Human-readable agent name.
        persona: System prompt / personality description.
        goals: List of agent goals/objectives.
        memfs: Optional MemFS instance for memory storage.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        persona: str = "",
        goals: list[str] | None = None,
        memfs: Any = None,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.persona = persona
        self.goals = goals or []
        self.memfs = memfs

        self._sessions: dict[str, AgentSession] = {}
        self._created_at = datetime.now(timezone.utc).isoformat()
        self._metadata: dict[str, Any] = {}

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    @property
    def active_sessions(self) -> list[AgentSession]:
        return [s for s in self._sessions.values() if s.is_active]

    async def create_session(
        self,
        user_input: str,
        user_id: str = "default",
    ) -> AgentSession:
        """Create a new session for this agent.

        Args:
            user_input: The initial user message.
            user_id: The user identifier.

        Returns:
            A new AgentSession instance.
        """
        session_id = str(uuid.uuid4())[:16]
        session = AgentSession(
            session_id=session_id,
            agent_id=self.agent_id,
            user_id=user_id,
            context={"initial_input": user_input},
        )
        self._sessions[session_id] = session

        logger.info(
            "agent_session_created",
            agent_id=self.agent_id,
            session_id=session_id,
            user_id=user_id,
        )

        return session

    async def get_session(self, session_id: str) -> AgentSession | None:
        """Get an existing session by ID."""
        return self._sessions.get(session_id)

    async def end_session(self, session_id: str) -> None:
        """Mark a session as ended."""
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            logger.info(
                "agent_session_ended",
                agent_id=self.agent_id,
                session_id=session_id,
                messages=session.message_count,
            )

    async def remember(
        self,
        fact: str,
        category: str = "episodic",
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> str | None:
        """Store a fact in the agent's memory.

        Writes the fact to the agent's MemFS under the appropriate
        category directory.

        Args:
            fact: The fact or memory to store.
            category: Memory category (episodic, preference, fact, decision).
            importance: Importance score (0.0-1.0).
            tags: Optional tags for categorization.

        Returns:
            The path where the memory was stored, or None on failure.
        """
        if self.memfs is None:
            logger.warning("agent_remember_no_memfs", agent_id=self.agent_id)
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = f"reference/{category}/{timestamp}_{uuid.uuid4().hex[:8]}.md"

        content = f"**Category:** {category}\n"
        content += f"**Importance:** {importance}\n"
        if tags:
            content += f"**Tags:** {', '.join(tags)}\n"
        content += f"**Date:** {datetime.now(timezone.utc).isoformat()}\n\n"
        content += fact

        try:
            from app.core.memfs.memory_block import MemoryBlock

            block = MemoryBlock.new(
                path=path,
                content=content,
                description=f"{category} memory: {fact[:60]}",
                category="reference",
                importance=importance,
                tags=tags or [category],
            )
            await self.memfs.write_block(block)

            logger.info(
                "agent_remembered",
                agent_id=self.agent_id,
                path=path,
                category=category,
            )
            return path
        except Exception as e:
            logger.error("agent_remember_failed", agent_id=self.agent_id, error=str(e))
            return None

    async def recall(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search the agent's memory for relevant facts.

        Uses the MemFS search capability to find memories
        matching the query.

        Args:
            query: The search query.
            limit: Maximum number of results.

        Returns:
            List of matching memory entries with path and content.
        """
        if self.memfs is None:
            return []

        try:
            results = await self.memfs.search(query)
            formatted = []
            for result in results[:limit]:
                formatted.append({
                    "path": result["path"],
                    "matches": result["matches"],
                    "total_matches": result["total_matches"],
                })
            return formatted
        except Exception as e:
            logger.error("agent_recall_failed", agent_id=self.agent_id, error=str(e))
            return []

    async def get_persona_block(self) -> str:
        """Get the agent's persona as a formatted block for prompt injection.

        Returns:
            Formatted persona string for system prompt.
        """
        if self.memfs is not None:
            try:
                persona_content = await self.memfs.read("system/persona.md")
                if persona_content.strip():
                    return persona_content
            except FileNotFoundError:
                pass

        lines = [f"# Agent: {self.name}"]
        if self.persona:
            lines.append(self.persona)
        if self.goals:
            lines.append("\n## Goals")
            lines.extend(f"- {g}" for g in self.goals)
        return "\n".join(lines)

    async def update_persona(self, new_persona: str) -> None:
        """Update the agent's persona and persist to memory."""
        self.persona = new_persona

        if self.memfs is not None:
            try:
                from app.core.memfs.memory_block import MemoryBlock

                block = MemoryBlock.new(
                    path="system/persona.md",
                    content=new_persona,
                    description="Agent identity, values, and behavior rules",
                    category="system",
                    importance=1.0,
                    tags=["system", "identity"],
                )
                await self.memfs.write_block(block)
            except Exception as e:
                logger.error("agent_update_persona_failed", error=str(e))

    async def add_goal(self, goal: str) -> None:
        """Add a new goal for the agent."""
        if goal not in self.goals:
            self.goals.append(goal)
            logger.info("agent_goal_added", agent_id=self.agent_id, goal=goal)

    async def remove_goal(self, goal: str) -> None:
        """Remove a goal from the agent."""
        if goal in self.goals:
            self.goals.remove(goal)
            logger.info("agent_goal_removed", agent_id=self.agent_id, goal=goal)

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent identity to dict."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "persona": self.persona,
            "goals": self.goals,
            "created_at": self._created_at,
            "session_count": self.session_count,
            "active_sessions": len(self.active_sessions),
            "metadata": self._metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentIdentity:
        """Create an AgentIdentity from a dict."""
        agent = cls(
            agent_id=data["agent_id"],
            name=data["name"],
            persona=data.get("persona", ""),
            goals=data.get("goals", []),
        )
        agent._created_at = data.get("created_at", agent._created_at)
        agent._metadata = data.get("metadata", {})
        return agent


class AgentRegistry:
    """Registry for managing multiple agent identities.

    Provides centralized agent lifecycle management with
    persistence and lookup capabilities.
    """

    def __init__(self, default_memfs_base: str = "./data/agents") -> None:
        self._agents: dict[str, AgentIdentity] = {}
        self._default_memfs_base = default_memfs_base
        logger.info("agent_registry_initialized")

    def register(self, agent: AgentIdentity) -> None:
        """Register an agent identity."""
        self._agents[agent.agent_id] = agent
        logger.info("agent_registered", agent_id=agent.agent_id, name=agent.name)

    def get(self, agent_id: str) -> AgentIdentity | None:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [agent.to_dict() for agent in self._agents.values()]

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("agent_unregistered", agent_id=agent_id)
            return True
        return False

    async def create_agent(
        self,
        name: str,
        persona: str = "",
        goals: list[str] | None = None,
        agent_id: str | None = None,
        memfs: Any = None,
    ) -> AgentIdentity:
        """Create and register a new agent.

        Args:
            name: Agent name.
            persona: Agent persona/system prompt.
            goals: Agent goals.
            agent_id: Optional explicit ID (generated if not provided).
            memfs: Optional MemFS instance.

        Returns:
            The created AgentIdentity.
        """
        aid = agent_id or f"agent-{uuid.uuid4().hex[:12]}"

        if memfs is None:
            from app.core.memfs import MemFS

            memfs_path = f"{self._default_memfs_base}/{aid}/memfs"
            memfs = MemFS(memfs_path)
            await memfs.init_defaults()

        agent = AgentIdentity(
            agent_id=aid,
            name=name,
            persona=persona,
            goals=goals or [],
            memfs=memfs,
        )

        self.register(agent)
        return agent
