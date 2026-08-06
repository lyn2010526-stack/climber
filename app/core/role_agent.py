"""Role-based Agent Definition (CrewAI style).

Provides a declarative agent model with role/goal/backstory identity fields,
tool assignment, and automatic system prompt construction. The AgentRegistry
manages multiple agents with YAML/Python definition support.

Reference: CrewAI's Agent class with role, goal, backstory identity fields.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

import structlog

from app.core.memfs import MemFS

logger = structlog.get_logger()


SYSTEM_PROMPT_TEMPLATE = """# Role
{role}

## Goal
{goal}

## Backstory
{backstory}

## Identity
- Agent ID: {agent_id}
- Name: {name}

## Behavior Rules
- Stay in character at all times. Your responses should reflect your role, goal, and backstory.
- Use your tools when they help accomplish your goal.
- Be direct and avoid unnecessary preamble or postamble.
- When uncertain, state your confidence level rather than guessing.
- Learn from interactions and adapt your approach based on what works.

{memory_block}
"""


@dataclass
class LLMConfig:
    """LLM configuration for an agent."""

    provider: str = "openai"
    model_id: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: float = 60.0


@dataclass
class AgentProfile:
    """Declarative agent identity definition.

    Each agent has a role (what they do), goal (what they pursue),
    and backstory (behavioral context for the LLM).
    """

    id: str = field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:12]}")
    name: str = "Assistant"
    role: str = "General Assistant"
    goal: str = "Help users accomplish their tasks effectively."
    backstory: str = "You are a helpful AI assistant."
    tools: list[str] = field(default_factory=list)
    memory_enabled: bool = True
    max_iter: int = 15
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def system_prompt(self, memory_context: str = "") -> str:
        """Build system prompt from role + goal + backstory.

        Args:
            memory_context: Optional memory block text injected into the prompt.

        Returns:
            Formatted system prompt string.
        """
        memory_block = ""
        if memory_context:
            memory_block = f"## Memory Context\n{memory_context}"

        return SYSTEM_PROMPT_TEMPLATE.format(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            agent_id=self.id,
            name=self.name,
            memory_block=memory_block,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize profile to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": self.tools,
            "memory_enabled": self.memory_enabled,
            "max_iter": self.max_iter,
            "llm_config": self.llm_config.__dict__,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProfile:
        """Create profile from dictionary."""
        llm_data = data.pop("llm_config", {})
        profile = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        profile.llm_config = LLMConfig(**llm_data)
        return profile


@runtime_checkable
class ToolProvider(Protocol):
    """Protocol for tool lookup."""

    def get_tool_schema(self, tool_id: str) -> dict[str, Any] | None: ...


class RoleAgent:
    """CrewAI-style agent with role/goal/backstory identity.

    Wraps an AgentProfile with runtime capabilities: session management,
    memory integration, and tool schema resolution.

    Args:
        profile: The agent's identity profile.
        tool_provider: Optional tool provider for schema resolution.
        memfs: Optional MemFS instance for memory storage.
    """

    def __init__(
        self,
        profile: AgentProfile,
        tool_provider: ToolProvider | None = None,
        memfs: MemFS | None = None,
    ) -> None:
        self.profile = profile
        self._tool_provider = tool_provider
        self._memfs = memfs
        self._session_id: str | None = None
        self._message_count: int = 0
        self._iteration_count: int = 0

    @property
    def agent_id(self) -> str:
        return self.profile.id

    @property
    def is_active(self) -> bool:
        return self._session_id is not None

    async def build_system_prompt(self) -> str:
        """Construct the full system prompt with memory context.

        Returns:
            Complete system prompt with memory injection if available.
        """
        memory_context = ""
        if self.profile.memory_enabled and self._memfs is not None:
            memory_context = await self._load_memory_context()

        return self.profile.system_prompt(memory_context)

    async def _load_memory_context(self) -> str:
        """Load relevant memory context from MemFS.

        Returns:
            Formatted memory context string.
        """
        parts: list[str] = []

        try:
            persona = await self._memfs.read("system/persona.md")
            if persona.strip():
                parts.append(f"### Persona\n{persona.strip()}")
        except FileNotFoundError:
            pass

        try:
            human = await self._memfs.read("system/human.md")
            if human.strip():
                parts.append(f"### User Context\n{human.strip()}")
        except FileNotFoundError:
            pass

        return "\n\n".join(parts)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Resolve tool schemas from the tool provider.

        Returns:
            List of tool schema dicts for tools assigned to this agent.
        """
        if self._tool_provider is None:
            return []

        schemas: list[dict[str, Any]] = []
        for tool_id in self.profile.tools:
            schema = self._tool_provider.get_tool_schema(tool_id)
            if schema is not None:
                schemas.append(schema)

        return schemas

    def start_session(self, session_id: str | None = None) -> str:
        """Start a new interaction session.

        Args:
            session_id: Optional explicit session ID.

        Returns:
            The session ID.
        """
        self._session_id = session_id or str(uuid.uuid4())[:16]
        self._message_count = 0
        self._iteration_count = 0
        logger.info(
            "role_agent_session_started",
            agent_id=self.agent_id,
            session_id=self._session_id,
        )
        return self._session_id

    def end_session(self) -> None:
        """End the current session."""
        if self._session_id:
            logger.info(
                "role_agent_session_ended",
                agent_id=self.agent_id,
                session_id=self._session_id,
                messages=self._message_count,
                iterations=self._iteration_count,
            )
        self._session_id = None

    def record_message(self) -> None:
        """Record a message exchange in the session."""
        self._message_count += 1

    def record_iteration(self) -> None:
        """Record an agent loop iteration."""
        self._iteration_count += 1

    @property
    def can_iterate(self) -> bool:
        """Check if the agent can continue iterating."""
        return self._iteration_count < self.profile.max_iter

    def to_dict(self) -> dict[str, Any]:
        """Serialize agent state to dictionary."""
        return {
            "profile": self.profile.to_dict(),
            "session_id": self._session_id,
            "message_count": self._message_count,
            "iteration_count": self._iteration_count,
            "is_active": self.is_active,
            "tool_schemas": self.get_tool_schemas(),
        }


class AgentRegistry:
    """Central registry for managing multiple role-based agents.

    Provides agent lifecycle management: create, retrieve, list, and remove.
    Supports YAML/Python agent definitions through dict-based factory methods.

    Args:
        default_memfs_base: Base directory for agent MemFS storage.
    """

    def __init__(self, default_memfs_base: str = "./data/agents") -> None:
        self._agents: dict[str, RoleAgent] = {}
        self._profiles: dict[str, AgentProfile] = {}
        self._default_memfs_base = default_memfs_base
        logger.info("agent_registry_initialized")

    @property
    def count(self) -> int:
        return len(self._agents)

    def register(self, agent: RoleAgent) -> None:
        """Register a role agent.

        Args:
            agent: The RoleAgent instance to register.
        """
        self._agents[agent.agent_id] = agent
        self._profiles[agent.agent_id] = agent.profile
        logger.info(
            "role_agent_registered",
            agent_id=agent.agent_id,
            name=agent.profile.name,
            role=agent.profile.role,
        )

    def get(self, agent_id: str) -> RoleAgent | None:
        """Get an agent by ID.

        Args:
            agent_id: The agent identifier.

        Returns:
            The RoleAgent if found, None otherwise.
        """
        return self._agents.get(agent_id)

    def get_profile(self, agent_id: str) -> AgentProfile | None:
        """Get an agent's profile by ID.

        Args:
            agent_id: The agent identifier.

        Returns:
            The AgentProfile if found, None otherwise.
        """
        return self._profiles.get(agent_id)

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents.

        Returns:
            List of agent state dictionaries.
        """
        return [agent.to_dict() for agent in self._agents.values()]

    def list_profiles(self) -> list[AgentProfile]:
        """List all registered agent profiles.

        Returns:
            List of AgentProfile instances.
        """
        return list(self._profiles.values())

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Args:
            agent_id: The agent identifier.

        Returns:
            True if the agent was removed, False if not found.
        """
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            agent.end_session()
            del self._agents[agent_id]
            del self._profiles[agent_id]
            logger.info("role_agent_unregistered", agent_id=agent_id)
            return True
        return False

    async def create_agent(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        tools: list[str] | None = None,
        memory_enabled: bool = True,
        max_iter: int = 15,
        llm_config: LLMConfig | None = None,
        agent_id: str | None = None,
        memfs: MemFS | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RoleAgent:
        """Create and register a new role agent.

        Args:
            name: Human-readable agent name.
            role: Agent role title (e.g. "Senior Data Researcher").
            goal: What the agent pursues.
            backstory: Behavioral context for the LLM.
            tools: List of tool IDs available to the agent.
            memory_enabled: Whether the agent uses persistent memory.
            max_iter: Maximum agent loop iterations per session.
            llm_config: LLM configuration.
            agent_id: Optional explicit ID.
            memfs: Optional MemFS instance.
            metadata: Additional metadata.

        Returns:
            The created and registered RoleAgent.
        """
        profile = AgentProfile(
            id=agent_id or f"agent-{uuid.uuid4().hex[:12]}",
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            tools=tools or [],
            memory_enabled=memory_enabled,
            max_iter=max_iter,
            llm_config=llm_config or LLMConfig(),
            metadata=metadata or {},
        )

        if memfs is None and memory_enabled:
            memfs_path = f"{self._default_memfs_base}/{profile.id}/memfs"
            memfs = MemFS(memfs_path)
            await memfs.init_defaults()

        agent = RoleAgent(profile=profile, memfs=memfs)
        self.register(agent)

        logger.info(
            "role_agent_created",
            agent_id=profile.id,
            name=name,
            role=role,
            tools=tools,
        )
        return agent

    async def from_dict(self, data: dict[str, Any]) -> RoleAgent:
        """Create an agent from a dictionary definition (YAML/Python).

        Args:
            data: Dictionary with agent definition fields.

        Returns:
            The created and registered RoleAgent.
        """
        llm_data = data.pop("llm_config", {})
        llm_config = LLMConfig(**llm_data) if llm_data else LLMConfig()

        memfs = None
        if data.get("memory_enabled", True):
            agent_id = data.get("id", f"agent-{uuid.uuid4().hex[:12]}")
            memfs_path = f"{self._default_memfs_base}/{agent_id}/memfs"
            memfs = MemFS(memfs_path)
            await memfs.init_defaults()

        profile = AgentProfile.from_dict({**data, "llm_config": llm_config.__dict__})
        agent = RoleAgent(profile=profile, memfs=memfs)
        self.register(agent)
        return agent

    async def load_definitions(
        self,
        definitions: list[dict[str, Any]],
    ) -> list[RoleAgent]:
        """Load multiple agent definitions.

        Args:
            definitions: List of agent definition dicts.

        Returns:
            List of created RoleAgent instances.
        """
        agents: list[RoleAgent] = []
        for definition in definitions:
            try:
                agent = await self.from_dict(definition)
                agents.append(agent)
            except Exception as e:
                logger.error(
                    "role_agent_load_failed",
                    definition=definition.get("name", "unknown"),
                    error=str(e),
                )
        return agents
