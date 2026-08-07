"""Tool: file_writer."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileWriterToolInput:
    """Tool input."""
    action: str = ''
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileWriterToolOutput:
    """Tool output."""
    success: bool = False
    result: Any = None
    error: str | None = None


class FileWriterTool:
    """Tool."""

    def __init__(self):
        self._name = 'file_writer'
        self._description = 'FileWriter tool'
        self._version = '1.0.0'

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def description(self) -> str:
        """Get description."""
        return self._description

    async def execute(self, inp: FileWriterToolInput) -> FileWriterToolOutput:
        """Execute."""
        try:
            result = await self._execute_impl(inp)
            return FileWriterToolOutput(success=True, result=result)
        except Exception as e:
            logger.error(f'Tool error: {e}')
            return FileWriterToolOutput(success=False, error=str(e))

    async def _execute_impl(self, inp: FileWriterToolInput) -> Any:
        """Implementation."""
        return {'action': inp.action, 'params': inp.params}
