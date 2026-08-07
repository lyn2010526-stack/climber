"""Reflection module — self-evaluation, quality scoring, and improvement suggestions.

Provides metacognitive capabilities:
- Self-evaluation: Multi-dimensional assessment of execution results
- Improvement advisory: Actionable suggestions based on evaluation
- Reflection engine: Post-execution analysis and strategy adjustment
"""

from __future__ import annotations

from app.reflection.improvement import ImprovementAdvisor, ImprovementSuggestion
from app.reflection.reflection_engine import ReflectionEngine, ReflectionResult
from app.reflection.self_evaluation import EvaluationResult, QualityScore, SelfEvaluator

__all__ = [
    "SelfEvaluator",
    "EvaluationResult",
    "QualityScore",
    "ImprovementAdvisor",
    "ImprovementSuggestion",
    "ReflectionEngine",
    "ReflectionResult",
]
