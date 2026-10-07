"""Built-in agent profiles and role definitions."""

from app.core.agents.registry import (
    BuiltinAgentProfile,
    RoleDefinition,
    get_builtin_agent,
    list_builtin_agents,
    register_builtin_agent,
    resolve_builtin_agent,
)

__all__ = [
    "BuiltinAgentProfile",
    "RoleDefinition",
    "get_builtin_agent",
    "list_builtin_agents",
    "register_builtin_agent",
    "resolve_builtin_agent",
]
