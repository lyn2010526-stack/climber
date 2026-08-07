#!/usr/bin/env python3
"""Bulk code generator 2 - Additional modules for expansion."""

from __future__ import annotations

from pathlib import Path
from string import Template

BASE = Path("/workspace/agent-engine")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


SKILL_TEMPLATE = Template('''\
"""Skill module: ${name} - ${description}."""

from __future__ import annotations

from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger()


class ${class_name}InputType(str, Enum):
    TEXT = "text"
    JSON = "json"
    FILE = "file"
    URL = "url"
    IMAGE = "image"


class ${class_name}OutputType(str, Enum):
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


@dataclass
class ${class_name}Config:
    """Configuration for ${name} skill."""
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
class ${class_name}Result:
    """Result of ${name} skill execution."""
    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ${class_name}Metrics:
    """Metrics tracking for ${name} skill."""
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


class ${class_name}Skill:
    """${description}."""

    def __init__(self, config: ${class_name}Config | None = None):
        self.config = config or ${class_name}Config()
        self.metrics = ${class_name}Metrics()
        self._cache: dict[str, tuple[Any, float]] = {}
        self._middleware: list[callable] = []

    def add_middleware(self, middleware: callable) -> None:
        """Add processing middleware."""
        self._middleware.append(middleware)

    async def execute(self, input_data: Any, input_type: str = "text", **kwargs: Any) -> ${class_name}Result:
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
            return ${class_name}Result(success=True, data=result_data, duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            self.metrics.record_call(False, duration, type(e).__name__)
            logger.error("${class_name} skill failed", error=str(e))
            return ${class_name}Result(success=False, error=str(e), duration_ms=duration)

    async def execute_batch(self, items: list[Any], **kwargs: Any) -> list[${class_name}Result]:
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
        self.metrics = ${class_name}Metrics()


class ${class_name}SkillRegistry:
    """Registry for managing ${name} skill instances."""

    def __init__(self):
        self._skills: dict[str, ${class_name}Skill] = {}
        self._configs: dict[str, ${class_name}Config] = {}

    def register(self, name: str, skill: ${class_name}Skill) -> None:
        """Register a skill instance."""
        self._skills[name] = skill
        logger.info("Registered ${class_name} skill", name=name)

    def get(self, name: str) -> ${class_name}Skill | None:
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

    async def execute(self, name: str, data: Any, **kwargs: Any) -> ${class_name}Result:
        """Execute a named skill."""
        skill = self.get(name)
        if not skill:
            return ${class_name}Result(success=False, error=f"Skill not found: {name}")
        return await skill.execute(data, **kwargs)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all skills."""
        return {name: skill.get_metrics() for name, skill in self._skills.items()}
''')


SKILL_TEST_TEMPLATE = Template('''\
"""Tests for ${name} skill - ${description}."""

import pytest
from unittest.mock import AsyncMock, patch

from app.skills.${name}_skill import (
    ${class_name}Skill,
    ${class_name}SkillRegistry,
    ${class_name}Config,
    ${class_name}Result,
    ${class_name}Metrics,
    ${class_name}InputType,
    ${class_name}OutputType,
)


@pytest.fixture
def config() -> ${class_name}Config:
    return ${class_name}Config(
        enabled=True,
        timeout_seconds=10,
        max_retries=2,
        validate_input=True,
        validate_output=True,
    )


@pytest.fixture
def skill(config: ${class_name}Config) -> ${class_name}Skill:
    return ${class_name}Skill(config)


@pytest.fixture
def registry() -> ${class_name}SkillRegistry:
    return ${class_name}SkillRegistry()


class Test${class_name}Config:
    """Tests for skill configuration."""

    def test_default_config(self):
        config = ${class_name}Config()
        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.batch_size == 10

    def test_custom_config(self, config):
        assert config.timeout_seconds == 10
        assert config.max_retries == 2


class Test${class_name}SkillExecution:
    """Tests for skill execution."""

    @pytest.mark.asyncio
    async def test_execute_success(self, skill):
        result = await skill.execute("test input")
        assert result.success is True
        assert result.data is not None

    @pytest.mark.asyncio
    async def test_execute_with_none_input(self, skill):
        result = await skill.execute(None)
        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_text_validation(self, skill):
        result = await skill.execute(123, input_type="text")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_json_validation(self, skill):
        result = await skill.execute("not json", input_type="json")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_valid_json(self, skill):
        result = await skill.execute({"key": "value"}, input_type="json")
        assert result.success is True


class Test${class_name}BatchExecution:
    """Tests for batch execution."""

    @pytest.mark.asyncio
    async def test_batch_execute(self, skill):
        items = ["item1", "item2", "item3"]
        results = await skill.execute_batch(items)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_batch_with_configured_size(self):
        config = ${class_name}Config(batch_size=2)
        skill = ${class_name}Skill(config)
        items = ["a", "b", "c", "d", "e"]
        results = await skill.execute_batch(items)
        assert len(results) == 5


class Test${class_name}Cache:
    """Tests for skill caching."""

    def test_set_and_get_cache(self, skill):
        skill.set_cache("test_key", "test_value")
        result = skill.get_cache("test_key")
        assert result == "test_value"

    def test_cache_miss(self, skill):
        result = skill.get_cache("nonexistent")
        assert result is None

    def test_clear_cache(self, skill):
        skill.set_cache("key1", "val1")
        skill.set_cache("key2", "val2")
        skill.clear_cache()
        assert skill.get_cache("key1") is None
        assert skill.get_cache("key2") is None


class Test${class_name}Metrics:
    """Tests for metrics tracking."""

    def test_initial_metrics(self, skill):
        metrics = skill.get_metrics()
        assert metrics["total_calls"] == 0
        assert metrics["successful_calls"] == 0

    @pytest.mark.asyncio
    async def test_metrics_after_call(self, skill):
        await skill.execute("test")
        metrics = skill.get_metrics()
        assert metrics["total_calls"] == 1
        assert metrics["successful_calls"] == 1

    @pytest.mark.asyncio
    async def test_metrics_after_failure(self, skill):
        await skill.execute(None)
        metrics = skill.get_metrics()
        assert metrics["total_calls"] == 1
        assert metrics["failed_calls"] == 1

    def test_reset_metrics(self, skill):
        skill.metrics.record_call(True, 100)
        skill.reset_metrics()
        assert skill.metrics.total_calls == 0


class Test${class_name}SkillRegistry:
    """Tests for skill registry."""

    def test_register_and_get(self, registry, skill):
        registry.register("test_skill", skill)
        result = registry.get("test_skill")
        assert result is skill

    def test_list_skills(self, registry, skill):
        registry.register("skill1", skill)
        registry.register("skill2", skill)
        skills = registry.list_skills()
        assert len(skills) == 2

    def test_unregister(self, registry, skill):
        registry.register("temp", skill)
        result = registry.unregister("temp")
        assert result is True
        assert registry.get("temp") is None

    @pytest.mark.asyncio
    async def test_execute_registered(self, registry, skill):
        registry.register("test", skill)
        result = await registry.execute("test", "input")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unregistered(self, registry):
        result = await registry.execute("nonexistent", "input")
        assert result.success is False


class Test${class_name}Middleware:
    """Tests for middleware support."""

    @pytest.mark.asyncio
    async def test_add_middleware(self, skill):
        async def transform(data):
            return data.upper() if isinstance(data, str) else data

        skill.add_middleware(transform)
        result = await skill.execute("hello")
        assert result.success is True


class Test${class_name}Result:
    """Tests for result object."""

    def test_success_result(self):
        result = ${class_name}Result(success=True, data="output")
        assert result.success is True
        assert result.error is None

    def test_error_result(self):
        result = ${class_name}Result(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class Test${class_name}Enums:
    """Tests for enum values."""

    def test_input_types(self):
        assert ${class_name}InputType.TEXT.value == "text"
        assert ${class_name}InputType.JSON.value == "json"
        assert ${class_name}InputType.FILE.value == "file"

    def test_output_types(self):
        assert ${class_name}OutputType.TEXT.value == "text"
        assert ${class_name}OutputType.JSON.value == "json"
        assert ${class_name}OutputType.HTML.value == "html"
''')


def main() -> None:
    all_files: dict[str, str] = {}

    skills = [
        ("text_summarizer", "Summarize long text documents"),
        ("sentiment_analyzer", "Analyze text sentiment and emotions"),
        ("language_detector", "Detect language of input text"),
        ("entity_extractor", "Extract named entities from text"),
        ("keyword_extractor", "Extract key phrases and terms"),
        ("translator", "Translate text between languages"),
        ("code_analyzer", "Analyze code quality and patterns"),
        ("code_generator", "Generate code from descriptions"),
        ("code_reviewer", "Review code for issues and improvements"),
        ("test_generator", "Generate unit tests for code"),
        ("documentation_generator", "Generate documentation from code"),
        ("data_classifier", "Classify data into categories"),
        ("anomaly_detector", "Detect anomalies in data patterns"),
        ("trend_analyzer", "Analyze trends in time series data"),
        ("forecasting_engine", "Generate forecasts from historical data"),
        ("image_classifier", "Classify images into categories"),
        ("ocr_processor", "Extract text from images"),
        ("chart_generator", "Generate charts from data"),
        ("report_formatter", "Format data into reports"),
        ("csv_processor", "Process and transform CSV data"),
        ("json_transformer", "Transform JSON data structures"),
        ("xml_parser", "Parse and extract data from XML"),
        ("markdown_renderer", "Render markdown to HTML"),
        ("html_sanitizer", "Sanitize HTML content"),
        ("url_shortener", "Generate short URLs"),
        ("qr_generator", "Generate QR codes"),
        ("pdf_extractor", "Extract text from PDF files"),
        ("spreadsheet_processor", "Process spreadsheet data"),
        ("calendar_manager", "Manage calendar events and schedules"),
        ("contact_manager", "Manage contact information"),
    ]

    print(f"Generating {len(skills)} skill modules with tests...")

    for name, desc in skills:
        class_name = "".join(w.capitalize() for w in name.split("_"))

        # Skill module
        skill_content = SKILL_TEMPLATE.substitute(
            name=name, description=desc, class_name=class_name
        )
        all_files[f"app/skills/{name}_skill.py"] = skill_content

        # Test module
        test_content = SKILL_TEST_TEMPLATE.substitute(
            name=name, description=desc, class_name=class_name
        )
        all_files[f"tests/test_{name}_skill.py"] = test_content

    print(f"Writing {len(all_files)} files...")
    for path_str, content in all_files.items():
        write_file(BASE / path_str, content)

    print(f"Done! Generated {len(all_files)} files across {len(skills)} skills.")


if __name__ == "__main__":
    main()
