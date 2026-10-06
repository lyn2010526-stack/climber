"""Skill Registry — comprehensive, de-duplicated skill system.

Categories:
- Core Agent: Self-Evolving, Memory, Governance, Research, Task Scheduler
- Engineering: Frontend, Backend, Full Stack, Database, DevOps, Git
- Quality: Code Review, Security Audit, TDD, Debugger
- Knowledge: Data Analysis, Tech Research, Doc Generator
- MCP Plugins: External service integrations
"""

import structlog

from app.skills.definitions import register_builtin_skills
from app.skills.registry import (
    LegacySkillRegistry,
    SkillCategory,
    SkillInfo,
)
from app.skills.registry import (
    SkillRegistry as _BaseSkillRegistry,
)

logger = structlog.get_logger()


class SkillRegistry(_BaseSkillRegistry):
    def __init__(self) -> None:
        super().__init__()
        register_builtin_skills(self)


# Global singleton
skill_registry = SkillRegistry()


__all__ = [
    "LegacySkillRegistry",
    "SkillCategory",
    "SkillInfo",
    "SkillRegistry",
    "register_builtin_skills",
    "skill_registry",
]
