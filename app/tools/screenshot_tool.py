"""Tool: screenshot."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotToolInput:
    """Tool input."""
    action: str = ''
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenshotToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class ScreenshotTool:
    """Tool."""

    def __init__(self):
        self._name = 'screenshot'
        self._description = 'Screenshot tool'
        self._version = '1.0.0'

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def description(self) -> str:
        """Get description."""
        return self._description

    async def execute(self, inp: ScreenshotToolInput) -> ScreenshotToolOutput:
        """Execute."""
        try:
            result = await self._execute_impl(inp)
            return ScreenshotToolOutput(success=True, result=result)
        except Exception as e:
            logger.error(f'Tool error: {e}')
            return ScreenshotToolOutput(success=False, error=str(e))

    async def _execute_impl(self, inp: ScreenshotToolInput) -> Any:
        """Implementation."""
        return {'action': inp.action, 'params': inp.params}
