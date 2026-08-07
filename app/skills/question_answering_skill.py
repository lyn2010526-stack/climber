"""Skill: question_answering."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QuestionAnsweringSkillConfig:
    """Skill config."""
    name: str = 'question_answering'
    description: str = ''
    enabled: bool = True
    priority: int = 0
    timeout: float = 30.0


@dataclass
class QuestionAnsweringSkillContext:
    """Skill context."""
    session_id: str = ''
    user_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuestionAnsweringSkillResult:
    """Skill result."""
    success: bool = False
    output: Any = None
    error: str | None = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


class QuestionAnsweringSkill:
    """Skill."""

    def __init__(self, config: QuestionAnsweringSkillConfig | None = None):
        self.config = config or QuestionAnsweringSkillConfig()
        self._middleware: list = []

    async def execute(self, context: QuestionAnsweringSkillContext, **params) -> QuestionAnsweringSkillResult:
        """Execute skill."""
        try:
            for mw in self._middleware:
                context = mw(context)
            output = await self._execute_impl(context, **params)
            return QuestionAnsweringSkillResult(success=True, output=output)
        except Exception as e:
            logger.error(f'Skill error: {e}')
            return QuestionAnsweringSkillResult(success=False, error=str(e))

    async def _execute_impl(self, context: QuestionAnsweringSkillContext, **params) -> Any:
        """Implementation."""
        return {'skill': self.config.name, 'params': params}

    def add_middleware(self, mw) -> None:
        """Add middleware."""
        self._middleware.append(mw)
