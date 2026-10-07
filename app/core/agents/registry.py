"""Small, dependency-free registry for built-in agent profiles.

Profiles are data-only contracts. The engine can opt into them without changing
the existing session or execution APIs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RoleDefinition:
    """Describe the responsibility and default prompt for a role."""

    role: str
    description: str = ""
    system_prompt: str = ""


@dataclass(frozen=True)
class BuiltinAgentProfile:
    """Declarative configuration consumed by optional agent integrations."""

    agent_id: str
    role: str
    system_prompt: str
    tool_ids: tuple[str, ...] = ()
    context_policy: dict[str, Any] = field(default_factory=dict)
    model_policy: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None
    lifecycle_events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id is required")
        if not self.role.strip():
            raise ValueError("role is required")


_ROLE_DEFINITIONS = {
    "assistant": RoleDefinition(
        role="assistant",
        description="General-purpose engineering assistant.",
        system_prompt="Act as a careful engineering assistant and keep work scoped.",
    ),
    "reviewer": RoleDefinition(
        role="reviewer",
        description="Reviews changes for correctness, regressions, and test gaps.",
        system_prompt="Review the supplied work for defects, risks, and missing validation.",
    ),
}

_BUILTIN_AGENTS: dict[str, BuiltinAgentProfile] = {
    "builtin.assistant": BuiltinAgentProfile(
        agent_id="builtin.assistant",
        role="assistant",
        system_prompt=_ROLE_DEFINITIONS["assistant"].system_prompt,
        context_policy={"include_task": True, "include_memory": True},
        model_policy={"temperature": 0.2},
        lifecycle_events=("started", "completed", "failed"),
    ),
    "builtin.reviewer": BuiltinAgentProfile(
        agent_id="builtin.reviewer",
        role="reviewer",
        system_prompt=_ROLE_DEFINITIONS["reviewer"].system_prompt,
        context_policy={"include_task": True, "include_memory": False},
        model_policy={"temperature": 0.0},
        output_schema={"type": "object", "required": ["findings"]},
        lifecycle_events=("started", "completed", "failed"),
    ),
}


def register_builtin_agent(profile: BuiltinAgentProfile) -> BuiltinAgentProfile:
    """Register and return a profile, allowing application-level extensions."""
    _BUILTIN_AGENTS[profile.agent_id] = profile
    return profile


def get_builtin_agent(agent_id: str) -> BuiltinAgentProfile | None:
    """Return a profile when registered, otherwise ``None``."""
    return _BUILTIN_AGENTS.get(agent_id)


def resolve_builtin_agent(agent_id: str) -> BuiltinAgentProfile:
    """Resolve a profile or raise a useful lookup error."""
    profile = get_builtin_agent(agent_id)
    if profile is None:
        raise KeyError(f"unknown built-in agent: {agent_id}")
    return profile


def list_builtin_agents() -> tuple[BuiltinAgentProfile, ...]:
    """Return profiles in deterministic registration order."""
    return tuple(_BUILTIN_AGENTS.values())
