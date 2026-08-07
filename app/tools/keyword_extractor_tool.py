"""Tool: keyword_extractor."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KeywordExtractorToolInput:
    """Tool input."""
    action: str = ''
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class KeywordExtractorToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class KeywordExtractorTool:
    """Tool."""

    def __init__(self):
        self._name = 'keyword_extractor'
        self._description = 'KeywordExtractor tool'
        self._version = '1.0.0'

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def description(self) -> str:
        """Get description."""
        return self._description

    async def execute(self, inp: KeywordExtractorToolInput) -> KeywordExtractorToolOutput:
        """Execute."""
        try:
            result = await self._execute_impl(inp)
            return KeywordExtractorToolOutput(success=True, result=result)
        except Exception as e:
            logger.error(f'Tool error: {e}')
            return KeywordExtractorToolOutput(success=False, error=str(e))

    async def _execute_impl(self, inp: KeywordExtractorToolInput) -> Any:
        """Implementation."""
        return {'action': inp.action, 'params': inp.params}
