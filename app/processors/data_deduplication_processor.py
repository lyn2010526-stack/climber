"""Data processor: data_deduplication."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DataDeduplicationProcessorConfig:
    """Processor config."""
    name: str = 'data_deduplication'
    batch_size: int = 100
    max_retries: int = 3
    timeout: float = 30.0
    enabled: bool = True


@dataclass
class DataDeduplicationProcessorResult:
    """Processor result."""
    success: bool = False
    data: Any = None
    errors: list[str] = field(default_factory=list)
    processed_at: datetime = field(default_factory=datetime.utcnow)


class DataDeduplicationProcessor:
    """Data processor."""

    def __init__(self, config: DataDeduplicationProcessorConfig | None = None):
        self.config = config or DataDeduplicationProcessorConfig()
        self._preprocessors: list[Callable] = []
        self._postprocessors: list[Callable] = []
        self._error_handlers: list[Callable] = []

    def add_preprocessor(self, fn: Callable) -> None:
        """Add preprocessor."""
        self._preprocessors.append(fn)

    def add_postprocessor(self, fn: Callable) -> None:
        """Add postprocessor."""
        self._postprocessors.append(fn)

    def add_error_handler(self, fn: Callable) -> None:
        """Add error handler."""
        self._error_handlers.append(fn)

    async def process(self, data: Any) -> DataDeduplicationProcessorResult:
        """Process data."""
        result = DataDeduplicationProcessorResult()
        try:
            processed = data
            for fn in self._preprocessors:
                processed = fn(processed)
            processed = await self._process_impl(processed)
            for fn in self._postprocessors:
                processed = fn(processed)
            result.success = True
            result.data = processed
        except Exception as e:
            result.errors.append(str(e))
            for fn in self._error_handlers:
                fn(e)
            logger.error(f'Processing error: {e}')
        return result

    async def _process_impl(self, data: Any) -> Any:
        """Implementation."""
        return data

    async def process_batch(self, items: list[Any]) -> list[DataDeduplicationProcessorResult]:
        """Process batch."""
        results = []
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            for item in batch:
                results.append(await self.process(item))
        return results


class DataDeduplicationProcessorPipeline:
    """Processor pipeline."""

    def __init__(self):
        self._processors: list[DataDeduplicationProcessor] = []

    def add_processor(self, processor: DataDeduplicationProcessor) -> None:
        """Add processor."""
        self._processors.append(processor)

    async def execute(self, data: Any) -> DataDeduplicationProcessorResult:
        """Execute pipeline."""
        result = DataDeduplicationProcessorResult(success=True, data=data)
        for processor in self._processors:
            if not processor.config.enabled:
                continue
            result = await processor.process(result.data)
            if not result.success:
                break
        return result
