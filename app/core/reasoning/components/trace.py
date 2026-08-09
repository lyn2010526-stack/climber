"""Reasoning tracer — complete audit trail of all reasoning steps."""

from __future__ import annotations

import threading
import time
from typing import Any

import structlog

from app.core.reasoning.base import (
    CoverageReport,
    ReasoningMode,
    ReasoningTrace,
    PathTrace,
    RoundTrace,
)

logger = structlog.get_logger()


class ReasoningTracer:
    """Thread-safe accumulator for the full reasoning trace."""

    def __init__(self) -> None:
        self._trace = ReasoningTrace()
        self._lock = threading.Lock()
        self._path_starts: dict[str, float] = {}
        self._round_starts: dict[str, float] = {}
        self._active_path: str | None = None

    def start(self, task: str, mode: ReasoningMode) -> None:
        with self._lock:
            self._trace.request_task = task
            self._trace.strategy_selected = mode.value
            self._trace.created_at = time.time()
        logger.debug("Trace started", mode=mode.value)

    def record_path_start(self, path_type: str, candidate_id: str) -> None:
        with self._lock:
            self._active_path = candidate_id
            self._path_starts[candidate_id] = time.monotonic()
            path_trace = PathTrace(candidate_id=candidate_id, path_type=path_type)
            self._trace.path_traces.append(path_trace)
        logger.debug("Path started", path_type=path_type, candidate_id=candidate_id)

    def record_round(
        self,
        candidate_id: str,
        round_trace: RoundTrace,
    ) -> None:
        with self._lock:
            for path in self._trace.path_traces:
                if path.candidate_id == candidate_id:
                    path.rounds.append(round_trace)
                    break
        logger.debug(
            "Round recorded",
            candidate_id=candidate_id,
            round=round_trace.round_num,
            action=round_trace.action,
        )

    def record_path_end(self, candidate_id: str, confidence: float) -> None:
        with self._lock:
            duration = 0.0
            if candidate_id in self._path_starts:
                duration = (time.monotonic() - self._path_starts[candidate_id]) * 1000

            for path in self._trace.path_traces:
                if path.candidate_id == candidate_id:
                    path.final_confidence = confidence
                    break

            if self._active_path == candidate_id:
                self._active_path = None

        logger.debug(
            "Path ended",
            candidate_id=candidate_id,
            confidence=confidence,
            duration_ms=f"{duration:.0f}",
        )

    def record_coverage(self, coverage: CoverageReport) -> None:
        with self._lock:
            self._trace.coverage_checks.append(
                {
                    "score": coverage.score,
                    "edge_cases_count": len(coverage.edge_cases),
                    "risks_count": len(coverage.risks),
                    "assumptions_count": len(coverage.assumptions),
                    "blind_spots_count": len(coverage.blind_spots),
                    "checklist": coverage.checklist,
                    "high_risks": len(coverage.high_risks),
                }
            )
        logger.debug("Coverage recorded", score=coverage.score)

    def record_selection(self, reason: str) -> None:
        with self._lock:
            self._trace.final_selection_reason = reason
        logger.debug("Selection recorded", reason=reason[:100])

    def finish(self) -> ReasoningTrace:
        with self._lock:
            self._trace.total_duration_ms = (
                time.time() - self._trace.created_at
            ) * 1000
            trace = self._trace.model_copy()

        logger.info(
            "Trace finalized",
            trace_id=trace.trace_id,
            paths=len(trace.path_traces),
            duration_ms=f"{trace.total_duration_ms:.0f}",
        )
        return trace

    def get_active_path(self) -> str | None:
        with self._lock:
            return self._active_path

    def snapshot(self) -> ReasoningTrace:
        with self._lock:
            return self._trace.model_copy(deep=True)
