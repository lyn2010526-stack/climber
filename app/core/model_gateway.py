"""Model gateway with automatic failover and intelligent routing.

Provides:
- Multi-model registration with health tracking
- Automatic failover on model failure
- Task-based model routing (code, chat, analysis, etc.)
- Circuit breaker pattern for unhealthy models
- Cost-aware model selection
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ModelStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"


class TaskType(StrEnum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CHAT = "chat"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    RESEARCH = "research"
    SHELL_COMMAND = "shell_command"
    GENERAL = "general"


@dataclass
class ModelCapability:
    """Capabilities and constraints of a model."""

    model_id: str
    provider: str
    max_context_tokens: int = 8192
    max_output_tokens: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    cost_per_1k_input_tokens: float = 0.0
    cost_per_1k_output_tokens: float = 0.0
    avg_latency_ms: float = 0.0
    task_strengths: list[TaskType] = field(default_factory=list)
    status: ModelStatus = ModelStatus.HEALTHY
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_recovery_seconds: float = 60.0

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_failures / self.total_requests

    @property
    def is_available(self) -> bool:
        if self.status == ModelStatus.DISABLED:
            return False
        if self.status == ModelStatus.UNHEALTHY:
            if self.last_failure_time > 0 and (
                time.time() - self.last_failure_time
                > self.circuit_breaker_recovery_seconds
            ):
                return True
            return False
        return True

    def record_success(self, latency_ms: float = 0.0) -> None:
        self.total_requests += 1
        self.last_success_time = time.time()
        self.consecutive_failures = 0
        if self.status == ModelStatus.DEGRADED:
            self.status = ModelStatus.HEALTHY
        if latency_ms > 0:
            if self.avg_latency_ms == 0:
                self.avg_latency_ms = latency_ms
            else:
                self.avg_latency_ms = self.avg_latency_ms * 0.8 + latency_ms * 0.2

    def record_failure(self) -> None:
        self.total_requests += 1
        self.total_failures += 1
        self.last_failure_time = time.time()
        self.consecutive_failures += 1

        if self.consecutive_failures >= self.circuit_breaker_threshold:
            self.status = ModelStatus.UNHEALTHY
            logger.warning(
                "Model %s circuit breaker tripped after %d consecutive failures",
                self.model_id,
                self.consecutive_failures,
            )
        elif self.consecutive_failures >= 2:
            self.status = ModelStatus.DEGRADED

    def reset_circuit_breaker(self) -> None:
        self.consecutive_failures = 0
        if self.status == ModelStatus.UNHEALTHY:
            self.status = ModelStatus.DEGRADED


@dataclass
class RoutingDecision:
    """Result of a model routing decision."""

    model_id: str
    reason: str
    fallback_chain: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])


class ModelGateway:
    """Intelligent model gateway with failover and routing."""

    def __init__(self) -> None:
        self._models: dict[str, ModelCapability] = {}
        self._task_routes: dict[TaskType, list[str]] = {}
        self._default_model: str = ""
        self._cost_budget: float = -1.0

    def register_model(self, capability: ModelCapability) -> None:
        """Register a model with its capabilities."""
        self._models[capability.model_id] = capability
        if not self._default_model:
            self._default_model = capability.model_id
        logger.info("Registered model: %s (%s)", capability.model_id, capability.provider)

    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model."""
        if model_id in self._models:
            del self._models[model_id]
            if self._default_model == model_id:
                self._default_model = next(iter(self._models), "")
            for routes in self._task_routes.values():
                if model_id in routes:
                    routes.remove(model_id)
            return True
        return False

    def set_task_route(self, task_type: TaskType, model_ids: list[str]) -> None:
        """Set the preferred model chain for a task type."""
        self._task_routes[task_type] = model_ids

    def set_default_model(self, model_id: str) -> None:
        """Set the default fallback model."""
        self._default_model = model_id

    def set_cost_budget(self, budget: float) -> None:
        """Set the maximum cost per request (-1 for unlimited)."""
        self._cost_budget = budget

    def get_model(self, model_id: str) -> ModelCapability | None:
        """Get a model's capability info."""
        return self._models.get(model_id)

    def list_models(self) -> list[ModelCapability]:
        """List all registered models."""
        return list(self._models.values())

    def list_available(self) -> list[ModelCapability]:
        """List only available (healthy) models."""
        return [m for m in self._models.values() if m.is_available]

    def route(
        self,
        task_type: TaskType = TaskType.GENERAL,
        preferred_model: str | None = None,
        require_tools: bool = False,
    ) -> RoutingDecision:
        """Determine the best model for a task."""
        if preferred_model and preferred_model in self._models:
            model = self._models[preferred_model]
            if model.is_available:
                if not require_tools or model.supports_tools:
                    return RoutingDecision(
                        model_id=preferred_model,
                        reason="User preferred model",
                        fallback_chain=self._build_fallback_chain(preferred_model, task_type),
                    )

        task_chain = self._task_routes.get(task_type, [])
        fallback_chain: list[str] = []

        for model_id in task_chain:
            model = self._models.get(model_id)
            if model and model.is_available:
                if require_tools and not model.supports_tools:
                    continue
                fallback_chain = [m for m in task_chain if m != model_id and m in self._models]
                return RoutingDecision(
                    model_id=model_id,
                    reason=f"Task route: {task_type.value}",
                    fallback_chain=fallback_chain,
                    estimated_latency_ms=model.avg_latency_ms,
                )

        for model_id, model in self._models.items():
            if model.is_available:
                if require_tools and not model.supports_tools:
                    continue
                return RoutingDecision(
                    model_id=model_id,
                    reason="First available model",
                    fallback_chain=self._build_fallback_chain(model_id),
                    estimated_latency_ms=model.avg_latency_ms,
                )

        return RoutingDecision(
            model_id=self._default_model,
            reason="No healthy models, using default (may fail)",
            fallback_chain=[],
        )

    def _build_fallback_chain(
        self, primary: str, task_type: TaskType | None = None
    ) -> list[str]:
        """Build a fallback chain excluding the primary model."""
        chain: list[str] = []
        if task_type:
            for model_id in self._task_routes.get(task_type, []):
                if model_id != primary and model_id in self._models:
                    if self._models[model_id].is_available:
                        chain.append(model_id)
        for model_id, model in self._models.items():
            if model_id != primary and model_id not in chain and model.is_available:
                chain.append(model_id)
        return chain

    def record_success(
        self, model_id: str, latency_ms: float = 0.0
    ) -> None:
        """Record a successful request."""
        model = self._models.get(model_id)
        if model:
            model.record_success(latency_ms)

    def record_failure(self, model_id: str) -> None:
        """Record a failed request."""
        model = self._models.get(model_id)
        if model:
            model.record_failure()

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all models."""
        return {
            model_id: {
                "status": model.status.value,
                "failure_rate": round(model.failure_rate, 3),
                "total_requests": model.total_requests,
                "consecutive_failures": model.consecutive_failures,
                "avg_latency_ms": round(model.avg_latency_ms, 1),
                "is_available": model.is_available,
            }
            for model_id, model in self._models.items()
        }

    def get_routing_table(self) -> dict[str, list[str]]:
        """Get the current routing table."""
        return {
            task_type.value: models
            for task_type, models in self._task_routes.items()
        }

    def reset_circuit_breaker(self, model_id: str) -> bool:
        """Manually reset a model's circuit breaker."""
        model = self._models.get(model_id)
        if model:
            model.reset_circuit_breaker()
            return True
        return False

    def get_recommended_model(self, task_description: str) -> str:
        """Get a model recommendation based on task description keywords."""
        task_lower = task_description.lower()

        code_keywords = ["code", "function", "class", "debug", "refactor", "implement"]
        if any(kw in task_lower for kw in code_keywords):
            route = self._task_routes.get(TaskType.CODE_GENERATION, [])
            if route:
                return route[0]

        analysis_keywords = ["analyze", "review", "evaluate", "compare", "assess"]
        if any(kw in task_lower for kw in analysis_keywords):
            route = self._task_routes.get(TaskType.ANALYSIS, [])
            if route:
                return route[0]

        return self._default_model
