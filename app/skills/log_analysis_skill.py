"""Skill: log_analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogAnalysisSkillConfig:
    """Skill config."""
    name: str = 'log_analysis'
    description: str = ''
    enabled: bool = True
    priority: int = 0
    timeout: float = 30.0


@dataclass
class LogAnalysisSkillContext:
    """Skill context."""
    session_id: str = ''
    user_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LogAnalysisSkillResult:
    """Skill result."""
    success: bool = False
    output: Any = None
    error: str | None = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


class LogAnalysisSkill:
    """Skill."""

    def __init__(self, config: LogAnalysisSkillConfig | None = None):
        self.config = config or LogAnalysisSkillConfig()
        self._middleware: list = []

    async def execute(self, context: LogAnalysisSkillContext, **params) -> LogAnalysisSkillResult:
        """Execute skill."""
        try:
            for mw in self._middleware:
                context = mw(context)
            output = await self._execute_impl(context, **params)
            return LogAnalysisSkillResult(success=True, output=output)
        except Exception as e:
            logger.error(f'Skill error: {e}')
            return LogAnalysisSkillResult(success=False, error=str(e))

    async def _execute_impl(self, context: LogAnalysisSkillContext, **params) -> Any:
        """Implementation."""
        return {'skill': self.config.name, 'params': params}

    def add_middleware(self, mw) -> None:
        """Add middleware."""
        self._middleware.append(mw)
