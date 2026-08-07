"""Skill: incident_response."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IncidentResponseSkillConfig:
    """Skill config."""
    name: str = 'incident_response'
    description: str = ''
    enabled: bool = True
    priority: int = 0
    timeout: float = 30.0


@dataclass
class IncidentResponseSkillContext:
    """Skill context."""
    session_id: str = ''
    user_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentResponseSkillResult:
    """Skill result."""
    success: bool = False
    output: Any = None
    error: str | None = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


class IncidentResponseSkill:
    """Skill."""

    def __init__(self, config: IncidentResponseSkillConfig | None = None):
        self.config = config or IncidentResponseSkillConfig()
        self._middleware: list = []

    async def execute(self, context: IncidentResponseSkillContext, **params) -> IncidentResponseSkillResult:
        """Execute skill."""
        try:
            for mw in self._middleware:
                context = mw(context)
            output = await self._execute_impl(context, **params)
            return IncidentResponseSkillResult(success=True, output=output)
        except Exception as e:
            logger.error(f'Skill error: {e}')
            return IncidentResponseSkillResult(success=False, error=str(e))

    async def _execute_impl(self, context: IncidentResponseSkillContext, **params) -> Any:
        """Implementation."""
        return {'skill': self.config.name, 'params': params}

    def add_middleware(self, mw) -> None:
        """Add middleware."""
        self._middleware.append(mw)
