"""Prompt manager — handles prompt assembly and constraints."""

from __future__ import annotations

import hashlib
from typing import Any


class PromptManager:
    """Manages prompt assembly for agents."""

    def __init__(self) -> None:
        self._templates: dict[str, str] = {}
        self._constraints: list[str] = []

    def assemble_prompt(self, context: dict[str, Any] | None = None, **kwargs: Any) -> str:
        """Assemble a prompt from template and context."""
        agent_id = kwargs.pop("agent_id", None)
        if agent_id:
            return str(self.build(agent_id=agent_id, context=context, **kwargs)["system_prompt"])
        base = self._templates.get("default", "You are a helpful assistant.")
        if context:
            for key, value in context.items():
                base = base.replace(f"{{{key}}}", str(value))
        return base

    def build(
        self,
        *,
        agent_id: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build a prompt bundle with optional built-in agent profile metadata."""
        if agent_id:
            from app.core.agents import resolve_builtin_agent

            profile = resolve_builtin_agent(agent_id)
            prompt = profile.system_prompt
            source = f"builtin-agent:{profile.agent_id}"
            version = "1.0.0"
        else:
            prompt = self._templates.get("default", "You are a helpful assistant.")
            source = "prompt-manager:default"
            version = "unversioned"

        values = dict(context or {})
        values.update(kwargs)
        for key, value in values.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        return {
            "system_prompt": prompt,
            "metadata": {
                "agent_id": agent_id,
                "prompt_version": version,
                "prompt_hash": prompt_hash,
                "prompt_source": source,
            },
        }

    def assemble(
        self,
        *,
        agent_id: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Unified bundle assembly entry point."""
        return self.build(agent_id=agent_id, context=context, **kwargs)

    def get_active_constraints(self) -> list[str]:
        """Get active constraints."""
        return self._constraints

    def add_constraint(self, constraint: str) -> None:
        self._constraints.append(constraint)

    def register_template(self, name: str, template: str) -> None:
        self._templates[name] = template
