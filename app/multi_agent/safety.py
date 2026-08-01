"""Multi-agent safety guards.

Prevents and resolves:
- Deadlock (agents cycling without progress)
- Conflict (sustained disagreement)
- Unproductive communication (arguing without resolution)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConflictType(str, Enum):
    DISAGREEMENT = "disagreement"       # Different technical opinions
    SCOPE = "scope"                     # Disagreement on what to build
    APPROACH = "approach"               # How to implement
    PRIORITY = "priority"               # What to do first
    QUALITY = "quality"                 # Standards disagreement


class ResolutionStrategy(str, Enum):
    MAJORITY_VOTE = "majority_vote"     # Take the majority opinion
    HYBRID = "hybrid"                   # Merge both approaches
    ESCALATE = "escalate"               # Ask human
    ROTATE = "rotate"                   # Alternate between approaches
    EVIDENCE = "evidence"               # Require proof/benchmark
    SIMPLIFY = "simplify"               # Choose simpler approach


@dataclass
class ConflictRecord:
    """Record of an agent conflict."""
    conflict_type: ConflictType
    parties: list[str]
    description: str
    round_number: int
    attempts: int = 1
    resolved: bool = False
    resolution: str = ""


@dataclass
class CommunicationRule:
    """Rules for productive inter-agent communication."""
    max_rebuttals: int = 3        # Max back-and-forth on same point
    require_evidence: bool = True  # Claims need supporting evidence
    require_alternatives: bool = True  # Rejections need alternatives
    max_message_length: int = 2000  # Characters per message


class DeadlockDetector:
    """Detects when multi-agent system is stuck in a loop."""

    def __init__(
        self,
        max_rounds_without_progress: int = 5,
        max_total_rounds: int = 30,
        similarity_threshold: float = 0.8,
    ):
        self.max_rounds_without_progress = max_rounds_without_progress
        self.max_total_rounds = max_total_rounds
        self.similarity_threshold = similarity_threshold
        self._history: list[dict] = []

    def record_round(self, proposals: list[str], decisions: list[str]) -> dict:
        """Record a round and check for deadlock."""
        self._history.append({
            "proposals": proposals,
            "decisions": decisions,
            "round": len(self._history),
        })

        return self.check_deadlock()

    def check_deadlock(self) -> dict:
        """Check if system is in deadlock."""
        status = {"deadlock": False, "reason": "", "suggestion": ""}

        # Check max rounds
        if len(self._history) >= self.max_total_rounds:
            status["deadlock"] = True
            status["reason"] = f"Max rounds ({self.max_total_rounds}) reached"
            status["suggestion"] = "Terminate with best solution so far"
            return status

        # Check stagnation
        if len(self._history) >= self.max_rounds_without_progress:
            recent = self._history[-self.max_rounds_without_progress:]
            # Check if proposals are stagnating (similar to each other)
            if self._are_similar(recent):
                status["deadlock"] = True
                status["reason"] = f"No progress in last {self.max_rounds_without_progress} rounds"
                status["suggestion"] = "Try a different approach or escalate to human"
                return status

        return status

    def _are_similar(self, rounds: list[dict]) -> bool:
        """Check if recent rounds are too similar (stagnation)."""
        if len(rounds) < 2:
            return False

        # Simple heuristic: check if proposals repeat
        all_props = []
        for r in rounds:
            all_props.extend(r.get("proposals", []))

        if not all_props:
            return False

        # If we have many proposals but few unique ones, it's stagnation
        unique_ratio = len(set(all_props)) / len(all_props)
        return unique_ratio < 0.5  # Less than 50% unique = stagnation


class ConflictArbitrator:
    """Resolves conflicts between agents."""

    def __init__(self):
        self._conflicts: list[ConflictRecord] = []
        self._resolutions: dict[ConflictType, ResolutionStrategy] = {
            ConflictType.DISAGREEMENT: ResolutionStrategy.EVIDENCE,
            ConflictType.SCOPE: ResolutionStrategy.ESCALATE,
            ConflictType.APPROACH: ResolutionStrategy.HYBRID,
            ConflictType.PRIORITY: ResolutionStrategy.MAJORITY_VOTE,
            ConflictType.QUALITY: ResolutionStrategy.SIMPLIFY,
        }

    def register_conflict(self, conflict: ConflictRecord):
        """Register a new conflict."""
        # Check if this is a repeat
        for existing in self._conflicts:
            if (existing.conflict_type == conflict.conflict_type and
                existing.parties == conflict.parties and
                not existing.resolved):
                existing.attempts += 1
                logger.warning(
                    "Recurring conflict (attempt %d): %s between %s",
                    existing.attempts, conflict.conflict_type.value, conflict.parties,
                )
                return

        self._conflicts.append(conflict)
        logger.info(
            "New conflict registered: %s between %s",
            conflict.conflict_type.value, conflict.parties,
        )

    def resolve(self, conflict: ConflictRecord) -> dict:
        """Attempt to resolve a conflict."""
        strategy = self._resolutions.get(conflict.conflict_type, ResolutionStrategy.ESCALATE)

        # If too many attempts, escalate
        if conflict.attempts >= 3:
            strategy = ResolutionStrategy.ESCALATE

        resolution = {
            "strategy": strategy.value,
            "action": self._apply_strategy(strategy, conflict),
            "escalate": strategy == ResolutionStrategy.ESCALATE,
        }

        if resolution["action"]:
            conflict.resolved = True
            conflict.resolution = resolution["action"]

        return resolution

    def _apply_strategy(self, strategy: ResolutionStrategy, conflict: ConflictRecord) -> str:
        """Apply a resolution strategy."""
        actions = {
            ResolutionStrategy.MAJORITY_VOTE: "Take the approach with most support",
            ResolutionStrategy.HYBRID: "Combine elements from both approaches",
            ResolutionStrategy.ESCALATE: "Request human decision",
            ResolutionStrategy.ROTATE: "Try one approach, then the other",
            ResolutionStrategy.EVIDENCE: "Run a benchmark/test to decide",
            ResolutionStrategy.SIMPLIFY: "Choose the simpler, more maintainable approach",
        }
        return actions.get(strategy, "Escalate to human")

    def get_unresolved(self) -> list[ConflictRecord]:
        """Get all unresolved conflicts."""
        return [c for c in self._conflicts if not c.resolved]


class CommunicationEnforcer:
    """Enforces productive communication rules between agents."""

    def __init__(self, rules: CommunicationRule | None = None):
        self.rules = rules or CommunicationRule()
        self._rebuttal_count: dict[str, int] = {}

    def check_message(self, sender: str, content: str, topic: str = "") -> dict:
        """Check if a message follows communication rules."""
        issues = []

        # Check length
        if len(content) > self.rules.max_message_length:
            issues.append(f"Message exceeds max length ({self.rules.max_message_length} chars)")

        # Check for evidence in claims
        if self.rules.require_evidence:
            has_claim = any(word in content.lower() for word in ["should", "must", "better", "worse"])
            has_evidence = any(word in content.lower() for word in ["because", "test", "benchmark", "data", "example"])
            if has_claim and not has_evidence:
                issues.append("Claims should include evidence")

        # Track rebuttals
        if topic:
            rebuttal_key = f"{topic}:{sender}"
            self._rebuttal_count[rebuttal_key] = self._rebuttal_count.get(rebuttal_key, 0) + 1
            if self._rebuttal_count[rebuttal_key] > self.rules.max_rebuttals:
                issues.append(f"Max rebuttals ({self.rules.max_rebuttals}) reached for topic '{topic}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def reset_topic(self, topic: str):
        """Reset rebuttal count for a topic."""
        keys_to_remove = [k for k in self._rebuttal_count if k.startswith(f"{topic}:")]
        for k in keys_to_remove:
            del self._rebuttal_count[k]
