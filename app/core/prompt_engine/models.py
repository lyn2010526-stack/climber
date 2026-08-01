"""Data models for the three-layer prompt engine."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class PromptLayer(IntEnum):
    """Prompt layers ordered by priority (lowest first, highest overrides).

    Layer 0: Immutable base — core agent rules, cannot be overridden
    Layer 1: Session template — user-editable persona, style, constraints
    Layer 2: Dynamic runtime — auto-injected by system (permissions, sandbox, etc.)
    """

    IMMUTABLE_BASE = 0
    SESSION_TEMPLATE = 1
    DYNAMIC_RUNTIME = 2


@dataclass
class PromptFragment:
    """A single piece of prompt content with metadata."""

    content: str
    layer: PromptLayer
    priority: int = 0
    source: str = ""
    token_cost: int = 0
    condition: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def render(self, context: dict[str, Any] | None = None) -> str:
        """Render fragment with optional variable substitution."""
        if not context:
            return self.content
        result = self.content
        for key, value in context.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result


@dataclass
class PromptTemplate:
    """A reusable prompt template that can be saved, imported, exported."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled"
    description: str = ""
    content: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    model_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    is_builtin: bool = False

    def render(self, variables: dict[str, str] | None = None) -> str:
        """Render template with variable substitution."""
        result = self.content
        vars = {**self.variables, **(variables or {})}
        for key, value in vars.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for export."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "variables": self.variables,
            "tags": self.tags,
            "model_id": self.model_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTemplate:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            content=data.get("content", ""),
            variables=data.get("variables", {}),
            tags=data.get("tags", []),
            model_id=data.get("model_id"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            is_builtin=data.get("is_builtin", False),
        )


@dataclass
class ModelAdaptation:
    """Model-specific prompt adaptation for different LLM backends."""

    model_id: str
    tool_call_format: str = "json"
    system_prefix: str = ""
    system_suffix: str = ""
    tool_instruction: str = ""
    error_reflection_prompt: str = ""
    max_system_tokens: int = 8192
    special_constraints: list[str] = field(default_factory=list)

    def adapt_base_prompt(self, base_prompt: str) -> str:
        """Apply model-specific adaptations to base prompt."""
        parts = []
        if self.system_prefix:
            parts.append(self.system_prefix)
        parts.append(base_prompt)
        if self.tool_instruction:
            parts.append(self.tool_instruction)
        if self.system_suffix:
            parts.append(self.system_suffix)
        return "\n\n".join(parts)


@dataclass
class RuntimeContext:
    """Dynamic context that influences prompt assembly."""

    user_id: str = ""
    session_id: str = ""
    agent_id: str = ""
    autonomous_mode: bool = False
    sandbox_enabled: bool = False
    mcp_ready: bool = False
    model_id: str = ""
    active_skills: list[str] = field(default_factory=list)
    permission_level: str = "standard"
    task_objective: str = ""
    custom_variables: dict[str, str] = field(default_factory=dict)
    multi_agent_mode: bool = False
    memory_retrieval_enabled: bool = False
    fault_recovery_enabled: bool = False
    group_id: str = ""
    task_id: str = ""
