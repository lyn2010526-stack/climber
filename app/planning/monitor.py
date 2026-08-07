"""Plan Monitor — execution tracking, deviation detection, and auto-correction.

Monitors plan execution in real-time, detects deviations from the expected
trajectory, and triggers corrective actions when necessary.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class PlanStatus(Enum):
    """Status of a monitored plan."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_TRACK = "on_track"
    DEVIATING = "deviating"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class CorrectiveAction(Protocol):
    """Protocol for corrective action handlers."""

    async def execute(self, deviation: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class ProgressSnapshot:
    """A snapshot of plan progress at a point in time."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    step_index: int = 0
    total_steps: int = 0
    status: PlanStatus = PlanStatus.NOT_STARTED
    current_output: str = ""
    expected_output: str = ""
    deviation_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def completion_pct(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.step_index / self.total_steps) * 100


@dataclass
class DeviationEvent:
    """A detected deviation from the plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    step_index: int = 0
    deviation_type: str = ""
    severity: float = 0.0
    description: str = ""
    suggested_action: str = ""
    auto_resolved: bool = False
    resolution: str = ""


@dataclass
class MonitorResult:
    """Result of plan monitoring session."""

    plan_id: str
    status: PlanStatus = PlanStatus.NOT_STARTED
    snapshots: list[ProgressSnapshot] = field(default_factory=list)
    deviations: list[DeviationEvent] = field(default_factory=list)
    corrections_applied: int = 0
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_deviations(self) -> int:
        return len(self.deviations)

    @property
    def unresolved_deviations(self) -> list[DeviationEvent]:
        return [d for d in self.deviations if not d.auto_resolved]

    @property
    def average_deviation_score(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.deviation_score for s in self.snapshots) / len(self.snapshots)


class PlanMonitor:
    """Monitors plan execution and triggers corrections."""

    def __init__(
        self,
        deviation_threshold: float = 0.5,
        max_corrections: int = 3,
        auto_correct: bool = True,
        corrective_handler: CorrectiveAction | None = None,
    ) -> None:
        self.deviation_threshold = deviation_threshold
        self.max_corrections = max_corrections
        self.auto_correct = auto_correct
        self.corrective_handler = corrective_handler
        self._snapshots: list[ProgressSnapshot] = []
        self._deviations: list[DeviationEvent] = []
        self._corrections_count = 0

    async def track_progress(
        self,
        plan_id: str,
        step_index: int,
        total_steps: int,
        current_output: str,
        expected_output: str = "",
    ) -> ProgressSnapshot:
        """Record a progress snapshot and check for deviations.

        Args:
            plan_id: The plan being tracked.
            step_index: Current step (0-based).
            total_steps: Total number of steps.
            current_output: Actual output at this step.
            expected_output: Expected output for comparison.

        Returns:
            A ProgressSnapshot with deviation analysis.
        """
        deviation_score = self._calculate_deviation(current_output, expected_output)

        status = self._determine_status(step_index, total_steps, deviation_score)

        snapshot = ProgressSnapshot(
            step_index=step_index,
            total_steps=total_steps,
            status=status,
            current_output=current_output,
            expected_output=expected_output,
            deviation_score=deviation_score,
        )

        self._snapshots.append(snapshot)

        if deviation_score >= self.deviation_threshold:
            deviation = await self._report_deviation(
                step_index, deviation_score, current_output, expected_output
            )
            self._deviations.append(deviation)

            if self.auto_correct and self._corrections_count < self.max_corrections:
                await self.auto_correct(deviation)

        logger.debug(
            "progress_tracked",
            plan_id=plan_id,
            step=step_index,
            deviation=deviation_score,
            status=status.value,
        )

        return snapshot

    async def detect_deviation(
        self,
        step_output: str,
        expected_pattern: str,
        step_index: int,
    ) -> DeviationEvent | None:
        """Detect if a step output deviates from expected.

        Args:
            step_output: The actual output.
            expected_pattern: Expected output pattern.
            step_index: The step index.

        Returns:
            DeviationEvent if deviation detected, None otherwise.
        """
        score = self._calculate_deviation(step_output, expected_pattern)

        if score >= self.deviation_threshold:
            return await self._report_deviation(
                step_index, score, step_output, expected_pattern
            )

        return None

    async def auto_correct(self, deviation: DeviationEvent) -> bool:
        """Attempt to auto-correct a deviation.

        Args:
            deviation: The deviation to correct.

        Returns:
            True if correction was applied successfully.
        """
        if self._corrections_count >= self.max_corrections:
            logger.warning("max_corrections_reached", max=self.max_corrections)
            return False

        self._corrections_count += 1

        if self.corrective_handler is not None:
            try:
                result = await self.corrective_handler.execute({
                    "deviation_type": deviation.deviation_type,
                    "step_index": deviation.step_index,
                    "severity": deviation.severity,
                    "description": deviation.description,
                })
                deviation.auto_resolved = result.get("success", False)
                deviation.resolution = result.get("resolution", "Handler applied")
                logger.info("deviation_auto_corrected", deviation_id=deviation.id)
            except Exception as e:
                deviation.resolution = f"Correction failed: {e}"
                logger.error("auto_correction_failed", error=str(e))
        else:
            deviation.auto_resolved = True
            deviation.resolution = "Marked for review (no handler configured)"

        return deviation.auto_resolved

    async def get_result(self, plan_id: str) -> MonitorResult:
        """Get the final monitoring result.

        Args:
            plan_id: The plan identifier.

        Returns:
            MonitorResult with all tracking data.
        """
        final_status = self._snapshots[-1].status if self._snapshots else PlanStatus.NOT_STARTED

        return MonitorResult(
            plan_id=plan_id,
            status=final_status,
            snapshots=list(self._snapshots),
            deviations=list(self._deviations),
            corrections_applied=self._corrections_count,
            success=final_status == PlanStatus.COMPLETED,
        )

    def reset(self) -> None:
        """Reset the monitor state."""
        self._snapshots.clear()
        self._deviations.clear()
        self._corrections_count = 0

    def _calculate_deviation(
        self,
        actual: str,
        expected: str,
    ) -> float:
        """Calculate deviation score between actual and expected output.

        Returns a value between 0 (identical) and 1 (completely different).
        """
        if not expected:
            return 0.0

        if not actual:
            return 1.0

        actual_words = set(actual.lower().split())
        expected_words = set(expected.lower().split())

        if not expected_words:
            return 0.0

        overlap = len(actual_words & expected_words)
        total = len(expected_words)

        similarity = overlap / total if total > 0 else 1.0
        return round(1.0 - similarity, 4)

    def _determine_status(
        self,
        step_index: int,
        total_steps: int,
        deviation_score: float,
    ) -> PlanStatus:
        """Determine the plan status based on current progress."""
        if step_index == 0 and total_steps == 0:
            return PlanStatus.NOT_STARTED

        if step_index >= total_steps - 1 and deviation_score < self.deviation_threshold:
            return PlanStatus.COMPLETED

        if deviation_score >= self.deviation_threshold * 1.5:
            return PlanStatus.BLOCKED

        if deviation_score >= self.deviation_threshold:
            return PlanStatus.DEVIATING

        if step_index > 0:
            return PlanStatus.ON_TRACK

        return PlanStatus.IN_PROGRESS

    async def _report_deviation(
        self,
        step_index: int,
        score: float,
        actual: str,
        expected: str,
    ) -> DeviationEvent:
        """Create a deviation event."""
        deviation_type = self._classify_deviation(score, actual, expected)

        return DeviationEvent(
            step_index=step_index,
            deviation_type=deviation_type,
            severity=score,
            description=(
                f"Step {step_index}: output deviates from expected. "
                f"Type: {deviation_type}, Severity: {score:.2f}"
            ),
            suggested_action=self._suggest_action(deviation_type),
        )

    def _classify_deviation(
        self,
        score: float,
        actual: str,
        expected: str,
    ) -> str:
        """Classify the type of deviation."""
        if not actual.strip():
            return "empty_output"

        if score > 0.8:
            return "content_mismatch"

        if len(actual) < len(expected) * 0.3:
            return "incomplete_output"

        if len(actual) > len(expected) * 3:
            return "verbose_output"

        return "partial_match"

    def _suggest_action(self, deviation_type: str) -> str:
        """Suggest corrective action based on deviation type."""
        actions = {
            "empty_output": "Retry step with more specific instructions",
            "content_mismatch": "Re-analyze requirements and adjust approach",
            "incomplete_output": "Extend step with additional context",
            "verbose_output": "Apply output filtering or summarization",
            "partial_match": "Minor adjustment to align with expectations",
        }
        return actions.get(deviation_type, "Review and adjust step parameters")
