"""Skill module: documentation_generator - Generate documentation from code."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class DocumentationGeneratorInputType(StrEnum):
    TEXT = "text"
    JSON = "json"
    FILE = "file"
    URL = "url"
    IMAGE = "image"


class DocumentationGeneratorOutputType(StrEnum):
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


@dataclass
class DocumentationGeneratorConfig:
    """Configuration for documentation_generator skill."""
    enabled: bool = True
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    batch_size: int = 10
    cache_ttl: int = 300
    log_level: str = "INFO"
    output_format: str = "json"
    validate_input: bool = True
    validate_output: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentationGeneratorResult:
    """Result of documentation_generator skill execution."""
    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentationGeneratorMetrics:
    """Metrics tracking for documentation_generator skill."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: float = 0
    avg_duration_ms: float = 0
    last_call_at: datetime | None = None
    errors_by_type: dict[str, int] = field(default_factory=dict)

    def record_call(self, success: bool, duration_ms: float, error_type: str | None = None) -> None:
        """Record a skill call."""
        self.total_calls += 1
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.total_calls
        self.last_call_at = datetime.utcnow()
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
            if error_type:
                self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1


class DocumentationGeneratorSkill:
    """Generate documentation from code."""

    def __init__(self, config: DocumentationGeneratorConfig | None = None):
        self.config = config or DocumentationGeneratorConfig()
        self.metrics = DocumentationGeneratorMetrics()
        self._cache: dict[str, tuple[Any, float]] = {}
        self._middleware: list[callable] = []

    def add_middleware(self, middleware: callable) -> None:
        """Add processing middleware."""
        self._middleware.append(middleware)

    async def execute(self, input_data: Any, input_type: str = "text", **kwargs: Any) -> DocumentationGeneratorResult:
        """Execute the skill."""
        import time
        start = time.time()

        try:
            if self.config.validate_input:
                input_data = await self._validate_input(input_data, input_type)

            for middleware in self._middleware:
                input_data = await middleware(input_data) if callable(middleware) else input_data

            result_data = await self._process(input_data, **kwargs)

            if self.config.validate_output:
                result_data = await self._validate_output(result_data)

            duration = (time.time() - start) * 1000
            self.metrics.record_call(True, duration)
            return DocumentationGeneratorResult(success=True, data=result_data, duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.metrics.record_call(False, duration, type(e).__name__)
            logger.error("DocumentationGenerator skill failed", error=str(e))
            return DocumentationGeneratorResult(success=False, error=str(e), duration_ms=duration)

    async def execute_batch(self, items: list[Any], **kwargs: Any) -> list[DocumentationGeneratorResult]:
        """Execute skill on a batch of items."""
        results = []
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            for item in batch:
                result = await self.execute(item, **kwargs)
                results.append(result)
        return results

    async def _validate_input(self, data: Any, input_type: str) -> Any:
        """Validate input data."""
        if data is None:
            raise ValueError("Input data cannot be None")
        if input_type == "text" and not isinstance(data, str):
            raise TypeError(f"Expected text input, got {type(data).__name__}")
        if input_type == "json" and not isinstance(data, (dict, list)):
            raise TypeError(f"Expected JSON input, got {type(data).__name__}")
        return data

    async def _validate_output(self, data: Any) -> Any:
        """Validate output data."""
        return data

    async def _process(self, data: Any, **kwargs: Any) -> Any:
        """Process input data - override in subclasses."""
        return data

    def get_cache(self, key: str) -> Any | None:
        """Get cached result."""
        if key in self._cache:
            value, expires = self._cache[key]
            if datetime.utcnow().timestamp() < expires:
                return value
            del self._cache[key]
        return None

    def set_cache(self, key: str, value: Any) -> None:
        """Cache a result."""
        self._cache[key] = (value, datetime.utcnow().timestamp() + self.config.cache_ttl)

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self._cache.clear()

    def get_metrics(self) -> dict[str, Any]:
        """Get skill metrics."""
        return {
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "avg_duration_ms": self.metrics.avg_duration_ms,
            "success_rate": self.metrics.successful_calls / max(1, self.metrics.total_calls),
            "last_call_at": self.metrics.last_call_at.isoformat() if self.metrics.last_call_at else None,
            "errors_by_type": self.metrics.errors_by_type,
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.metrics = DocumentationGeneratorMetrics()


class DocumentationGeneratorSkillRegistry:
    """Registry for managing documentation_generator skill instances."""

    def __init__(self):
        self._skills: dict[str, DocumentationGeneratorSkill] = {}
        self._configs: dict[str, DocumentationGeneratorConfig] = {}

    def register(self, name: str, skill: DocumentationGeneratorSkill) -> None:
        """Register a skill instance."""
        self._skills[name] = skill
        logger.info("Registered DocumentationGenerator skill", name=name)

    def get(self, name: str) -> DocumentationGeneratorSkill | None:
        """Get skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """List all registered skills."""
        return list(self._skills.keys())

    def unregister(self, name: str) -> bool:
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    async def execute(self, name: str, data: Any, **kwargs: Any) -> DocumentationGeneratorResult:
        """Execute a named skill."""
        skill = self.get(name)
        if not skill:
            return DocumentationGeneratorResult(success=False, error=f"Skill not found: {name}")
        return await skill.execute(data, **kwargs)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all skills."""
        return {name: skill.get_metrics() for name, skill in self._skills.items()}
