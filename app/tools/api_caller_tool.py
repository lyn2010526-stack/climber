"""Tool: api_caller."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ApiCallerToolInput:
    """Tool input."""
    action: str = ''
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApiCallerToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class ApiCallerTool:
    """Tool."""

    def __init__(self):
        self._name = 'api_caller'
        self._description = 'ApiCaller tool'
        self._version = '1.0.0'

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def description(self) -> str:
        """Get description."""
        return self._description

    async def execute(self, inp: ApiCallerToolInput) -> ApiCallerToolOutput:
        """Execute."""
        try:
            result = await self._execute_impl(inp)
            return ApiCallerToolOutput(success=True, result=result)
        except Exception as e:
            logger.error(f'Tool error: {e}')
            return ApiCallerToolOutput(success=False, error=str(e))

    async def _execute_impl(self, inp: ApiCallerToolInput) -> Any:
        """Implementation."""
        return {'action': inp.action, 'params': inp.params}
