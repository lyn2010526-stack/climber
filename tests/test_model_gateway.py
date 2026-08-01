"""Tests for the model gateway with failover and routing."""

from __future__ import annotations

import pytest

from app.core.model_gateway import (
    ModelCapability,
    ModelGateway,
    ModelStatus,
    RoutingDecision,
    TaskType,
)


class TestModelCapability:
    def test_default_status(self) -> None:
        cap = ModelCapability(model_id="test", provider="ollama")
        assert cap.status == ModelStatus.HEALTHY
        assert cap.is_available

    def test_record_success(self) -> None:
        cap = ModelCapability(model_id="test", provider="ollama")
        cap.record_success(latency_ms=100)
        assert cap.total_requests == 1
        assert cap.consecutive_failures == 0
        assert cap.avg_latency_ms == 100

    def test_record_failure(self) -> None:
        cap = ModelCapability(model_id="test", provider="ollama")
        cap.record_failure()
        assert cap.total_requests == 1
        assert cap.consecutive_failures == 1
        assert cap.status == ModelStatus.HEALTHY

    def test_circuit_breaker_trips(self) -> None:
        cap = ModelCapability(
            model_id="test",
            provider="ollama",
            circuit_breaker_threshold=3,
        )
        cap.record_failure()
        cap.record_failure()
        cap.record_failure()
        assert cap.status == ModelStatus.UNHEALTHY
        assert not cap.is_available

    def test_reset_circuit_breaker(self) -> None:
        cap = ModelCapability(
            model_id="test",
            provider="ollama",
            circuit_breaker_threshold=2,
        )
        cap.record_failure()
        cap.record_failure()
        assert cap.status == ModelStatus.UNHEALTHY
        cap.reset_circuit_breaker()
        assert cap.status == ModelStatus.DEGRADED
        assert cap.consecutive_failures == 0

    def test_failure_rate(self) -> None:
        cap = ModelCapability(model_id="test", provider="ollama")
        cap.record_success()
        cap.record_success()
        cap.record_failure()
        assert cap.failure_rate == pytest.approx(1 / 3)

    def test_disabled_model_unavailable(self) -> None:
        cap = ModelCapability(model_id="test", provider="ollama")
        cap.status = ModelStatus.DISABLED
        assert not cap.is_available


class TestModelGateway:
    def _make_cap(
        self, model_id: str, provider: str = "ollama", **kwargs
    ) -> ModelCapability:
        return ModelCapability(model_id=model_id, provider=provider, **kwargs)

    def test_register_model(self) -> None:
        gw = ModelGateway()
        cap = self._make_cap("llama3", "ollama")
        gw.register_model(cap)
        assert gw.get_model("llama3") is not None

    def test_unregister_model(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("test", "ollama"))
        assert gw.unregister_model("test")
        assert gw.get_model("test") is None

    def test_list_models(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("m1", "ollama"))
        gw.register_model(self._make_cap("m2", "ollama"))
        assert len(gw.list_models()) == 2

    def test_list_available(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("healthy", "ollama"))
        unhealthy = self._make_cap("unhealthy", "ollama")
        unhealthy.status = ModelStatus.UNHEALTHY
        gw.register_model(unhealthy)
        available = gw.list_available()
        assert len(available) == 1
        assert available[0].model_id == "healthy"

    def test_route_preferred_model(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("preferred", "ollama"))
        gw.register_model(self._make_cap("fallback", "ollama"))
        decision = gw.route(preferred_model="preferred")
        assert decision.model_id == "preferred"

    def test_route_with_task_type(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("code-model", "ollama"))
        gw.register_model(self._make_cap("chat-model", "ollama"))
        gw.set_task_route(TaskType.CODE_GENERATION, ["code-model"])
        decision = gw.route(task_type=TaskType.CODE_GENERATION)
        assert decision.model_id == "code-model"

    def test_route_fallback_when_preferred_unavailable(self) -> None:
        gw = ModelGateway()
        preferred = self._make_cap("preferred", "ollama")
        preferred.status = ModelStatus.UNHEALTHY
        gw.register_model(preferred)
        gw.register_model(self._make_cap("available", "ollama"))
        decision = gw.route(preferred_model="preferred")
        assert decision.model_id == "available"

    def test_route_require_tools(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("no-tools", "ollama", supports_tools=False))
        gw.register_model(self._make_cap("with-tools", "ollama", supports_tools=True))
        decision = gw.route(require_tools=True)
        assert decision.model_id == "with-tools"

    def test_record_success_and_failure(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("test", "ollama"))
        gw.record_success("test", latency_ms=50)
        gw.record_failure("test")
        cap = gw.get_model("test")
        assert cap is not None
        assert cap.total_requests == 2

    def test_get_health_status(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("test", "ollama"))
        status = gw.get_health_status()
        assert "test" in status
        assert status["test"]["status"] == "healthy"

    def test_reset_circuit_breaker(self) -> None:
        gw = ModelGateway()
        cap = self._make_cap("test", "ollama", circuit_breaker_threshold=1)
        gw.register_model(cap)
        gw.record_failure("test")
        assert gw.reset_circuit_breaker("test")
        assert cap.status == ModelStatus.DEGRADED

    def test_get_recommended_model_for_code(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("code-expert", "ollama"))
        gw.set_task_route(TaskType.CODE_GENERATION, ["code-expert"])
        recommended = gw.get_recommended_model("Write a Python function")
        assert recommended == "code-expert"

    def test_set_default_model(self) -> None:
        gw = ModelGateway()
        gw.register_model(self._make_cap("default", "ollama"))
        gw.set_default_model("default")
        assert gw._default_model == "default"
