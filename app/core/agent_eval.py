"""Agent evaluation and observability.

Provides metric definitions, evaluation results, an agent evaluator with
in-memory history, and a metrics collector with windowed averages.
"""

from __future__ import annotations

import re
import structlog
import time
from difflib import SequenceMatcher
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class EvalMetric(str, Enum):
    """Supported evaluation metrics."""

    ACCURACY = "accuracy"
    LATENCY = "latency"
    TOOL_SUCCESS = "tool_success"
    COMPLETION = "completion"
    COHERENCE = "coherence"


class EvalResult(BaseModel):
    """Result of evaluating a single agent task."""

    task_id: str
    agent_name: str
    metrics: dict[str, float] = Field(default_factory=dict)
    passed: bool
    duration_ms: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


_SENTENCE_RE = re.compile(r"[.!?。！？]+\s*")
_PARAGRAPH_RE = re.compile(r"\n{2,}")


class AgentEvaluator:
    """Evaluate agent outputs and keep an in-memory history of results."""

    def __init__(self) -> None:
        self._results: list[EvalResult] = []
        self._lock = __import__("asyncio").Lock()

    def _accuracy(self, expected: str, actual: str) -> float:
        """Return a similarity score in [0.0, 1.0] between expected and actual."""
        if not expected and not actual:
            return 1.0
        if not expected or not actual:
            return 0.0
        return SequenceMatcher(None, expected, actual).ratio()

    def _coherence(self, text: str) -> float:
        """Return a simple coherence score based on sentence and paragraph structure."""
        if not text or not text.strip():
            return 0.0
        stripped = text.strip()
        sentences = [s for s in _SENTENCE_RE.split(stripped) if s.strip()]
        paragraphs = [p for p in _PARAGRAPH_RE.split(stripped) if p.strip()]
        if not sentences:
            return 0.0
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        length_score = min(avg_len / 50.0, 1.0)
        paragraph_score = min(len(paragraphs) / 3.0, 1.0)
        return round(0.7 * length_score + 0.3 * paragraph_score, 4)

    async def evaluate(
        self,
        task: str,
        expected: str,
        agent_output: str,
        latency_ms: float = 0.0,
    ) -> EvalResult:
        """Evaluate a single agent output against an expected result."""
        accuracy = self._accuracy(expected, agent_output)
        coherence = self._coherence(agent_output)
        tool_success = 1.0 if accuracy >= 0.5 else 0.0
        completion = 1.0 if agent_output.strip() else 0.0
        latency_metric = max(0.0, 1.0 - latency_ms / 10000.0)
        metrics = {
            EvalMetric.ACCURACY.value: round(accuracy, 4),
            EvalMetric.LATENCY.value: round(latency_metric, 4),
            EvalMetric.TOOL_SUCCESS.value: tool_success,
            EvalMetric.COMPLETION.value: completion,
            EvalMetric.COHERENCE.value: coherence,
        }
        passed = accuracy >= 0.5 and bool(agent_output.strip())
        result = EvalResult(
            task_id=str(uuid4()),
            agent_name="default",
            metrics=metrics,
            passed=passed,
            duration_ms=latency_ms,
            details={"task": task, "expected": expected, "output": agent_output},
            created_at=time.time(),
        )
        async with self._lock:
            self._results.append(result)
        logger.info(
            "eval_result",
            task_id=result.task_id,
            passed=result.passed,
            accuracy=accuracy,
            latency_ms=latency_ms,
        )
        return result

    async def evaluate_batch(self, tasks: list[dict]) -> list[EvalResult]:
        """Evaluate a batch of tasks, each dict with task/expected/output/agent_name keys."""
        results: list[EvalResult] = []
        for item in tasks:
            task = str(item.get("task", ""))
            expected = str(item.get("expected", ""))
            agent_output = str(item.get("agent_output", ""))
            latency_ms = float(item.get("latency_ms", 0.0))
            result = await self.evaluate(task, expected, agent_output, latency_ms)
            if item.get("agent_name"):
                result.agent_name = str(item["agent_name"])
            if isinstance(item.get("details"), dict):
                result.details.update(item["details"])
            results.append(result)
        logger.info("eval_batch_completed", count=len(results))
        return results

    async def stats(self) -> dict:
        """Return aggregate statistics over the recorded evaluation history."""
        async with self._lock:
            results = list(self._results)
        if not results:
            return {
                "total": 0,
                "avg_score": 0.0,
                "pass_rate": 0.0,
                "avg_duration_ms": 0.0,
            }
        total = len(results)
        avg_score = sum(r.metrics.get(EvalMetric.ACCURACY.value, 0.0) for r in results) / total
        passed = sum(1 for r in results if r.passed)
        avg_duration = sum(r.duration_ms for r in results) / total
        return {
            "total": total,
            "avg_score": round(avg_score, 4),
            "pass_rate": round(passed / total, 4),
            "avg_duration_ms": round(avg_duration, 2),
        }


_WINDOW_SIZE = 100


class MetricsCollector:
    """Collect and aggregate observability metrics in memory."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}

    def _key(self, name: str, tags: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        tag_tuple = tuple(sorted((tags or {}).items()))
        return name, tag_tuple

    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a numeric sample for the named metric."""
        key = self._key(name, tags)
        window = self._values.setdefault(key, [])
        window.append(float(value))
        if len(window) > _WINDOW_SIZE:
            del window[: len(window) - _WINDOW_SIZE]

    def increment(self, name: str, tags: dict[str, str] | None = None) -> None:
        """Increment a counter for the named metric."""
        key = self._key(name, tags)
        self._counters[key] = self._counters.get(key, 0) + 1

    def timing(self, name: str, start_time: float) -> None:
        """Record the elapsed time in milliseconds since start_time."""
        self.record(name, (time.time() - start_time) * 1000.0)

    def snapshot(self) -> dict:
        """Return a snapshot of all recorded metrics and counters."""
        values = {}
        for (name, tags), samples in self._values.items():
            if not samples:
                continue
            metric = {
                "count": len(samples),
                "avg": round(sum(samples) / len(samples), 4),
                "min": round(min(samples), 4),
                "max": round(max(samples), 4),
            }
            if tags:
                metric["tags"] = dict(tags)
            values[name] = metric
        counters = {
            name: {"count": count, "tags": dict(tags) if tags else {}}
            for (name, tags), count in self._counters.items()
        }
        return {"values": values, "counters": counters}


_evaluator: AgentEvaluator | None = None
_collector: MetricsCollector | None = None


async def get_evaluator() -> AgentEvaluator:
    """Return the process-wide singleton AgentEvaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentEvaluator()
    return _evaluator


def get_collector() -> MetricsCollector:
    """Return the process-wide singleton MetricsCollector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
