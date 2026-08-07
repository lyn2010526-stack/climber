"""Tests for anomaly_detector skill - Detect anomalies in data patterns."""


import pytest

from app.skills.anomaly_detector_skill import (
    AnomalyDetectorConfig,
    AnomalyDetectorInputType,
    AnomalyDetectorOutputType,
    AnomalyDetectorResult,
    AnomalyDetectorSkill,
    AnomalyDetectorSkillRegistry,
)


@pytest.fixture
def config() -> AnomalyDetectorConfig:
    return AnomalyDetectorConfig(
        enabled=True,
        timeout_seconds=10,
        max_retries=2,
        validate_input=True,
        validate_output=True,
    )


@pytest.fixture
def skill(config: AnomalyDetectorConfig) -> AnomalyDetectorSkill:
    return AnomalyDetectorSkill(config)


@pytest.fixture
def registry() -> AnomalyDetectorSkillRegistry:
    return AnomalyDetectorSkillRegistry()


class TestAnomalyDetectorConfig:
    """Tests for skill configuration."""

    def test_default_config(self):
        config = AnomalyDetectorConfig()
        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.batch_size == 10

    def test_custom_config(self, config):
        assert config.timeout_seconds == 10
        assert config.max_retries == 2


class TestAnomalyDetectorSkillExecution:
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


class TestAnomalyDetectorBatchExecution:
    """Tests for batch execution."""

    @pytest.mark.asyncio
    async def test_batch_execute(self, skill):
        items = ["item1", "item2", "item3"]
        results = await skill.execute_batch(items)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_batch_with_configured_size(self):
        config = AnomalyDetectorConfig(batch_size=2)
        skill = AnomalyDetectorSkill(config)
        items = ["a", "b", "c", "d", "e"]
        results = await skill.execute_batch(items)
        assert len(results) == 5


class TestAnomalyDetectorCache:
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


class TestAnomalyDetectorMetrics:
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


class TestAnomalyDetectorSkillRegistry:
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


class TestAnomalyDetectorMiddleware:
    """Tests for middleware support."""

    @pytest.mark.asyncio
    async def test_add_middleware(self, skill):
        async def transform(data):
            return data.upper() if isinstance(data, str) else data

        skill.add_middleware(transform)
        result = await skill.execute("hello")
        assert result.success is True


class TestAnomalyDetectorResult:
    """Tests for result object."""

    def test_success_result(self):
        result = AnomalyDetectorResult(success=True, data="output")
        assert result.success is True
        assert result.error is None

    def test_error_result(self):
        result = AnomalyDetectorResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"


class TestAnomalyDetectorEnums:
    """Tests for enum values."""

    def test_input_types(self):
        assert AnomalyDetectorInputType.TEXT.value == "text"
        assert AnomalyDetectorInputType.JSON.value == "json"
        assert AnomalyDetectorInputType.FILE.value == "file"

    def test_output_types(self):
        assert AnomalyDetectorOutputType.TEXT.value == "text"
        assert AnomalyDetectorOutputType.JSON.value == "json"
        assert AnomalyDetectorOutputType.HTML.value == "html"
