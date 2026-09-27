"""Parameter adjuster — proposes the next parameter set after rejection.

Models the "自动调整参数重跑" loop from OpenFOAM-Agent / MatSciAgent:
when a probe rejects an attempt, the adjuster nudges parameters inside
declared bounds and returns a new candidate. The adjustment is bounded
and deterministic (no unbounded mutation), and stops when the max
attempt budget is exhausted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.simulation.models import ExperimentSpec
from app.simulation.planner import ParamDim


@dataclass
class AdjustConfig:
    """Bounded perturbation settings per parameter."""
    max_steps: int = 8  # max rounds per experiment
    perturb_ratio: float = 0.5  # relative step per retry
    reorder_attempts: int = 3  # how many perturb attempts before giving up


@dataclass
class ParameterAdjuster:
    """Deterministic parameter adjuster for retry rounds.

    Only parameters listed in ``adjustable`` (the plan's sweep dimensions)
    are perturbed. Fixed base parameters are never touched, so a retry
    cannot corrupt the physical constants of an experiment.
    """
    config: AdjustConfig = field(default_factory=AdjustConfig)
    bounds: dict[str, tuple[float | None, float | None]] = field(default_factory=dict)
    adjustable: set[str] = field(default_factory=set)

    def next_parameters(
        self,
        spec: ExperimentSpec,
        round_number: int,
    ) -> dict[str, Any] | None:
        """Return adjusted parameters for the given round, or None to stop."""
        if round_number >= self.config.max_steps:
            return None
        # Fall back to bounds keys for callers that only configure bounds
        # (legacy usage); from_plan_dims sets the explicit sweep dims.
        adjustable = self.adjustable or set(self.bounds)
        adjusted = dict(spec.parameters)
        for key, value in list(adjusted.items()):
            if key not in adjustable:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                lo, hi = self.bounds.get(key, (None, None))
                perturb = abs(value) * self.config.perturb_ratio if value else 1.0
                next_value = value - perturb * round_number
                if lo is not None and next_value < lo:
                    next_value = lo
                if hi is not None and next_value > hi:
                    next_value = hi
                adjusted[key] = next_value
        return adjusted

    @classmethod
    def from_plan_dims(cls, dims: list[ParamDim], max_steps: int = 8) -> "ParameterAdjuster":
        bounds: dict[str, tuple[float | None, float | None]] = {}
        adjustable: set[str] = set()
        for dim in dims:
            adjustable.add(dim.name)
            lo = dim.min
            hi = dim.max
            if lo is None or hi is None:
                # Fall back to the declared values only when the plan
                # gives no explicit numeric range. An explicit min/max
                # must win over a single-value ``values`` list, otherwise
                # a one-point sweep would freeze the adjuster at that value.
                if dim.values and all(isinstance(v, (int, float)) for v in dim.values):
                    lo = min(dim.values)
                    hi = max(dim.values)
            bounds[dim.name] = (lo, hi)
        return cls(config=AdjustConfig(max_steps=max_steps), bounds=bounds, adjustable=adjustable)