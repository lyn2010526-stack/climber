"""Tool: json_parser."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JsonParserToolInput:
    """Tool input."""
    action: str = ''
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class JsonParserToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class JsonParserTool:
    """Tool."""

    def __init__(self):
        self._name = 'json_parser'
        self._description = 'JsonParser tool'
        self._version = '1.0.0'

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def description(self) -> str:
        """Get description."""
        return self._description

    async def execute(self, inp: JsonParserToolInput) -> JsonParserToolOutput:
        """Execute."""
        try:
            result = await self._execute_impl(inp)
            return JsonParserToolOutput(success=True, result=result)
        except Exception as e:
            logger.error(f'Tool error: {e}')
            return JsonParserToolOutput(success=False, error=str(e))

    async def _execute_impl(self, inp: JsonParserToolInput) -> Any:
        """Implementation."""
        return {'action': inp.action, 'params': inp.params}
