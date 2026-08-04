"""Role-based agent specialization.

"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentRole:
    id: str
    name: str
    display_name: str
    description: str
    system_prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    allowed_models: list[str] = field(default_factory=list)
    max_iterations: int = 10
    allow_delegation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class RoleManager:
    """Manage agent roles and assignments."""

    def __init__(self):
        self._roles: dict[str, AgentRole] = {}
        self._default_roles: dict[str, AgentRole] = {}

    def register_role(self, role: AgentRole) -> None:
        self._roles[role.id] = role
        if role.id not in self._default_roles:
            self._default_roles[role.id] = role

    def get_role(self, role_id: str) -> AgentRole | None:
        return self._roles.get(role_id)

    def list_roles(self) -> list[AgentRole]:
        return list(self._roles.values())

    def create_default_roles(self) -> None:
        """Create default roles: planner, executor, reviewer."""
        if "planner" not in self._roles:
            self.register_role(AgentRole(
                id="planner",
                name="planner",
                display_name="规划智能体",
                description="Break down complex tasks into actionable steps",
                system_prompt="You are a planner agent. Break down complex tasks into clear, actionable steps.",
                allowed_tools=["search_memories", "core_memory_search"],
                max_iterations=5,
            ))
        if "executor" not in self._roles:
            self.register_role(AgentRole(
                id="executor",
                name="executor",
                display_name="执行智能体",
                description="Execute tasks using available tools",
                system_prompt="You are an executor agent. Execute tasks efficiently using available tools.",
                allowed_tools=[],
                max_iterations=10,
                allow_delegation=False,
            ))
        if "reviewer" not in self._roles:
            self.register_role(AgentRole(
                id="reviewer",
                name="reviewer",
                display_name="审核智能体",
                description="Review and validate outputs",
                system_prompt="You are a reviewer agent. Review outputs against requirements and provide feedback.",
                allowed_tools=["read_file", "file_diff"],
                max_iterations=5,
            ))


role_manager = RoleManager()
