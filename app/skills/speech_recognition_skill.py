"""Skill: speech_recognition."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpeechRecognitionSkillConfig:
    """Skill config."""
    name: str = 'speech_recognition'
    description: str = ''
    enabled: bool = True
    priority: int = 0
    timeout: float = 30.0


@dataclass
class SpeechRecognitionSkillContext:
    """Skill context."""
    session_id: str = ''
    user_id: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpeechRecognitionSkillResult:
    """Skill result."""
    success: bool = False
    output: Any = None
    error: str | None = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


class SpeechRecognitionSkill:
    """Skill."""

    def __init__(self, config: SpeechRecognitionSkillConfig | None = None):
        self.config = config or SpeechRecognitionSkillConfig()
        self._middleware: list = []

    async def execute(self, context: SpeechRecognitionSkillContext, **params) -> SpeechRecognitionSkillResult:
        """Execute skill."""
        try:
            for mw in self._middleware:
                context = mw(context)
            output = await self._execute_impl(context, **params)
            return SpeechRecognitionSkillResult(success=True, output=output)
        except Exception as e:
            logger.error(f'Skill error: {e}')
            return SpeechRecognitionSkillResult(success=False, error=str(e))

    async def _execute_impl(self, context: SpeechRecognitionSkillContext, **params) -> Any:
        """Implementation."""
        return {'skill': self.config.name, 'params': params}

    def add_middleware(self, mw) -> None:
        """Add middleware."""
        self._middleware.append(mw)
