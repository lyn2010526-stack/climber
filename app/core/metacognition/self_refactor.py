"""Self-Module Refactor — auto modify/merge/split stored skills.

After multiple tasks, eliminates low-performing skill patterns and
optimizes successful ones.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillPerformance:
    skill_name: str
    total_uses: int = 0
    successes: int = 0
    avg_tokens_used: float = 0.0
    avg_iterations: float = 0.0
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_uses == 0:
            return 0.0
        return self.successes / self.total_uses

    @property
    def efficiency_score(self) -> float:
        """Higher is better: high success, low token/iteration cost."""
        if self.total_uses == 0:
            return 0.0
        token_factor = max(0, 1 - self.avg_tokens_used / 10000)
        iter_factor = max(0, 1 - self.avg_iterations / 15)
        return self.success_rate * 0.5 + token_factor * 0.25 + iter_factor * 0.25


@dataclass
class RefactorAction:
    action: str  # "keep", "merge", "split", "deprecate", "optimize"
    target: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class SelfModuleRefactor:
    """Analyzes and refactors skill performance."""

    def __init__(self, storage_path: str = "data/skill_performance.json"):
        self._storage_path = storage_path
        self._performance: dict[str, SkillPerformance] = {}
        self._load()

    def record_skill_use(
        self,
        skill_name: str,
        success: bool,
        tokens_used: int,
        iterations: int,
    ) -> None:
        """Record a skill usage for performance tracking."""
        perf = self._performance.setdefault(
            skill_name, SkillPerformance(skill_name=skill_name)
        )
        perf.total_uses += 1
        if success:
            perf.successes += 1
        # Running average
        perf.avg_tokens_used = (
            perf.avg_tokens_used * (perf.total_uses - 1) + tokens_used
        ) / perf.total_uses
        perf.avg_iterations = (
            perf.avg_iterations * (perf.total_uses - 1) + iterations
        ) / perf.total_uses
        self._save()

    def analyze(self) -> list[RefactorAction]:
        """Analyze all skills and recommend refactor actions."""
        actions: list[RefactorAction] = []

        for name, perf in self._performance.items():
            if perf.total_uses < 3:
                actions.append(RefactorAction(
                    action="keep",
                    target=name,
                    reason=f"Insufficient data ({perf.total_uses} uses)",
                ))
                continue

            if perf.success_rate < 0.3 and perf.total_uses >= 5:
                actions.append(RefactorAction(
                    action="deprecate",
                    target=name,
                    reason=f"Low success rate: {perf.success_rate:.0%} over {perf.total_uses} uses",
                ))
            elif perf.efficiency_score > 0.7:
                actions.append(RefactorAction(
                    action="keep",
                    target=name,
                    reason=f"High efficiency: {perf.efficiency_score:.2f}",
                ))
            elif perf.avg_tokens_used > 8000:
                actions.append(RefactorAction(
                    action="optimize",
                    target=name,
                    reason=f"High token cost: {perf.avg_tokens_used:.0f} avg",
                    details={"suggestion": "Add early termination or context pruning"},
                ))
            elif perf.avg_iterations > 12:
                actions.append(RefactorAction(
                    action="split",
                    target=name,
                    reason=f"Too many iterations: {perf.avg_iterations:.0f} avg",
                    details={"suggestion": "Split into smaller, focused sub-skills"},
                ))
            else:
                actions.append(RefactorAction(
                    action="keep",
                    target=name,
                    reason=f"Acceptable performance: score={perf.efficiency_score:.2f}",
                ))

        return actions

    def get_performance(self, skill_name: str) -> SkillPerformance | None:
        return self._performance.get(skill_name)

    def get_all_performance(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.skill_name,
                "uses": p.total_uses,
                "success_rate": p.success_rate,
                "avg_tokens": p.avg_tokens_used,
                "avg_iterations": p.avg_iterations,
                "efficiency": p.efficiency_score,
            }
            for p in self._performance.values()
        ]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
        data = {
            name: {
                "skill_name": p.skill_name,
                "total_uses": p.total_uses,
                "successes": p.successes,
                "avg_tokens_used": p.avg_tokens_used,
                "avg_iterations": p.avg_iterations,
            }
            for name, p in self._performance.items()
        }
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        if not os.path.exists(self._storage_path):
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for name, p in data.items():
                self._performance[name] = SkillPerformance(
                    skill_name=p["skill_name"],
                    total_uses=p.get("total_uses", 0),
                    successes=p.get("successes", 0),
                    avg_tokens_used=p.get("avg_tokens_used", 0.0),
                    avg_iterations=p.get("avg_iterations", 0.0),
                )
        except (json.JSONDecodeError, KeyError):
            pass
