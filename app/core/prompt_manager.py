"""Prompt manager — handles prompt assembly and constraints."""
from __future__ import annotations
from typing import Any, Optional


class PromptManager:
    """Manages prompt assembly for agents."""
    
    def __init__(self):
        self._templates: dict[str, str] = {}
        self._constraints: list[str] = []
    
    def assemble_prompt(self, context: dict[str, Any] | None = None, **kwargs) -> str:
        """Assemble a prompt from template and context."""
        base = self._templates.get("default", "You are a helpful assistant.")
        if context:
            for key, value in context.items():
                base = base.replace(f"{{{key}}}", str(value))
        return base
    
    def get_active_constraints(self) -> list[str]:
        """Get active constraints."""
        return self._constraints
    
    def add_constraint(self, constraint: str) -> None:
        self._constraints.append(constraint)
    
    def register_template(self, name: str, template: str) -> None:
        self._templates[name] = template
