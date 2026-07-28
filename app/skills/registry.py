"""Skill registry — simplified, single-responsibility module.

This module only handles skill registration, discovery, and invocation.
Other concerns (composition, versioning, testing, anti-hallucination) are
moved to dedicated modules.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

import structlog
from pydantic import BaseModel

from app.core.interfaces import ISkillRegistry

logger = structlog.get_logger()


class SkillCategory(str, Enum):
    CORE = "core"
    ENGINEERING = "engineering"
    QUALITY = "quality"
    KNOWLEDGE = "knowledge"
    MCP = "mcp"


class SkillInfo(BaseModel):
    id: str
    name: str
    description: str
    category: SkillCategory
    icon: str = ""
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    enabled: bool = True
    is_mcp: bool = False
    mcp_config: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillInfo] = {}
        self._handlers: dict[str, Callable] = {}

    def register(self, skill: SkillInfo, handler: Callable | None = None) -> None:
        self._skills[skill.id] = skill
        if handler:
            self._handlers[skill.id] = handler
        logger.info("skill_registered", skill_id=skill.id, category=skill.category)

    def unregister(self, skill_id: str) -> bool:
        if skill_id in self._skills:
            del self._skills[skill_id]
            self._handlers.pop(skill_id, None)
            return True
        return False

    def get(self, skill_id: str) -> SkillInfo | None:
        return self._skills.get(skill_id)

    def get_handler(self, skill_id: str) -> Callable | None:
        return self._handlers.get(skill_id)

    def list_skills(self) -> list[dict[str, Any]]:
        return [skill.model_dump() for skill in self._skills.values()]

    def list_by_category(self, category: SkillCategory) -> list[SkillInfo]:
        return [s for s in self._skills.values() if s.category == category]

    def enable(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable(self, skill_id: str) -> bool:
        skill = self._skills.get(skill_id)
        if skill:
            skill.enabled = False
            return True
        return False

    async def invoke(self, skill_id: str, params: dict[str, Any]) -> Any:
        skill = self._skills.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        if not skill.enabled:
            raise ValueError(f"Skill is disabled: {skill_id}")
        handler = self._handlers.get(skill_id)
        if not handler:
            raise ValueError(f"No handler for skill: {skill_id}")
        if asyncio.iscoroutinefunction(handler):
            return await handler(**params)
        return handler(**params)


# Legacy compatibility: keep the old interface working
class LegacySkillRegistry(ISkillRegistry):
    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self._registry = registry or SkillRegistry()

    def register(self, skill: Any) -> None:
        self._registry.register(skill)

    def get(self, skill_id: str) -> Any | None:
        return self._registry.get(skill_id)

    def list_skills(self) -> list[dict[str, Any]]:
        return self._registry.list_skills()
