"""Role-Based Capability Boundaries.

Provides role definitions, capability registration, and enforcement
of capability boundaries at tool execution time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentRole(str, Enum):
    """Agent role types for capability boundary isolation."""

    PLANNER = "planner"
    EXECUTOR = "executor"
    AUDITOR = "auditor"
    RESEARCHER = "researcher"
    COMMUNICATOR = "communicator"
    GUARD = "guard"


@dataclass
class Capability:
    """Describes a capability with its requirements."""

    name: str
    description: str = ""
    required_tools: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required_tools": self.required_tools,
            "required_permissions": self.required_permissions,
        }


@dataclass
class RoleDefinition:
    """Defines a role with its capabilities and constraints."""

    role: AgentRole
    capabilities: list[Capability] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    max_iterations: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


class RoleRegistry:
    """Registry for role definitions and capability enforcement."""

    def __init__(self) -> None:
        self._roles: dict[AgentRole, RoleDefinition] = {}
        self._agent_roles: dict[str, AgentRole] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default role definitions."""
        self.register_role(RoleDefinition(
            role=AgentRole.PLANNER,
            capabilities=[
                Capability(name="task_decomposition", required_tools=["analyze"]),
                Capability(name="goal_setting", required_tools=["plan"]),
            ],
            allowed_tools=["analyze", "plan", "search"],
            allowed_actions=["create_task", "assign_task", "prioritize"],
            max_iterations=5,
        ))
        self.register_role(RoleDefinition(
            role=AgentRole.EXECUTOR,
            capabilities=[
                Capability(name="tool_execution", required_tools=["execute"]),
                Capability(name="code_generation", required_tools=["write", "edit"]),
            ],
            allowed_tools=["execute", "write", "edit", "read", "search"],
            allowed_actions=["execute_task", "report_result"],
            max_iterations=15,
        ))
        self.register_role(RoleDefinition(
            role=AgentRole.AUDITOR,
            capabilities=[
                Capability(name="quality_check", required_tools=["validate"]),
                Capability(name="compliance_verify", required_tools=["audit"]),
            ],
            allowed_tools=["read", "validate", "audit", "compare"],
            allowed_actions=["review", "approve", "reject"],
            max_iterations=5,
        ))
        self.register_role(RoleDefinition(
            role=AgentRole.RESEARCHER,
            capabilities=[
                Capability(name="information_gathering", required_tools=["search"]),
                Capability(name="analysis", required_tools=["analyze"]),
            ],
            allowed_tools=["search", "analyze", "read", "summarize"],
            allowed_actions=["research", "report"],
            max_iterations=10,
        ))
        self.register_role(RoleDefinition(
            role=AgentRole.COMMUNICATOR,
            capabilities=[
                Capability(name="message_routing", required_tools=["send"]),
                Capability(name="notification", required_tools=["notify"]),
            ],
            allowed_tools=["send", "notify", "receive", "broadcast"],
            allowed_actions=["send_message", "broadcast", "notify"],
            max_iterations=10,
        ))
        self.register_role(RoleDefinition(
            role=AgentRole.GUARD,
            capabilities=[
                Capability(name="safety_check", required_tools=["validate"]),
                Capability(name="access_control", required_tools=["authorize"]),
            ],
            allowed_tools=["validate", "authorize", "block", "audit"],
            allowed_actions=["check", "block", "allow", "escalate"],
            max_iterations=3,
        ))

    def register_role(self, definition: RoleDefinition) -> None:
        """Register or update a role definition."""
        self._roles[definition.role] = definition

    def get_capabilities(self, role: AgentRole) -> list[Capability]:
        """Get capabilities for a role."""
        definition = self._roles.get(role)
        if not definition:
            return []
        return list(definition.capabilities)

    def get_role_definition(self, role: AgentRole) -> RoleDefinition | None:
        """Get the full role definition."""
        return self._roles.get(role)

    def assign_role(self, agent_id: str, role: AgentRole) -> None:
        """Assign a role to an agent."""
        self._agent_roles[agent_id] = role

    def get_agent_role(self, agent_id: str) -> AgentRole | None:
        """Get the role assigned to an agent."""
        return self._agent_roles.get(agent_id)

    def check_permission(self, agent_id: str, tool_name: str) -> bool:
        """Check if an agent is permitted to use a tool based on its role."""
        role = self._agent_roles.get(agent_id)
        if not role:
            return False
        definition = self._roles.get(role)
        if not definition:
            return False
        return tool_name in definition.allowed_tools

    def check_action(self, agent_id: str, action: str) -> bool:
        """Check if an agent is permitted to perform an action."""
        role = self._agent_roles.get(agent_id)
        if not role:
            return False
        definition = self._roles.get(role)
        if not definition:
            return False
        return action in definition.allowed_actions

    def can_access_capability(self, agent_id: str, capability_name: str) -> bool:
        """Check if an agent's role includes a specific capability."""
        role = self._agent_roles.get(agent_id)
        if not role:
            return False
        definition = self._roles.get(role)
        if not definition:
            return False
        return any(c.name == capability_name for c in definition.capabilities)

    def list_roles(self) -> list[AgentRole]:
        """List all registered roles."""
        return list(self._roles.keys())

    def list_agent_roles(self) -> dict[str, AgentRole]:
        """List all agent-role assignments."""
        return dict(self._agent_roles)
