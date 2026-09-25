"""Planner — turns an engineering requirement into experiment candidates.

Configurations follow the parameter-space search strategy from
MatSciAgent / CircuitAgent: given a tool and a parameter space
(discrete values or numeric ranges), produce an explicit sweep of
candidate parameter sets. The sweep is bounded so a malicious or huge
space cannot cause unbounded tool dispatch.
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass, field
from typing import Any

from app.simulation.models import ExperimentSpec


@dataclass
class ParamDim:
    """One parameter dimension of the search space."""
    name: str
    values: list[Any] | None = None
    min: float | None = None
    max: float | None = None
    steps: int = 10

    def grid_values(self) -> list[Any]:
        if self.values:
            return self.values
        if self.min is not None and self.max is not None:
            if self.min == self.max:
                return [self.min]
            step = (self.max - self.min) / max(1, self.steps - 1)
            values: list[float] = []
            for i in range(max(1, self.steps)):
                value = self.min + step * i
                rounded = round(value, 6)
                if not values or rounded not in values:
                    values.append(rounded)
            if values[-1] != self.max:
                values.append(self.max)
            return values
        return [None]


@dataclass
class ExperimentPlan:
    """An explicit, bounded list of candidate experiments."""
    tool_name: str
    objective: str = ""
    base_parameters: dict[str, Any] = field(default_factory=dict)
    sweep_dims: list[ParamDim] = field(default_factory=list)
    experiments: list[ExperimentSpec] = field(default_factory=list)
    total: int = 0

    def build(self) -> "ExperimentPlan":
        """Materialize the Cartesian sweep into concrete experiments."""
        if self.experiments:
            return self
        axes: list[list[Any]] = []
        labels: list[str] = []
        for dim in self.sweep_dims:
            axis = dim.grid_values()
            labels.append(dim.name)
            axes.append(axis)
        combos = list(itertools.product(*axes)) if axes else [()]
        self.experiments = []
        for combo in combos:
            params = dict(self.base_parameters)
            for label, value in zip(labels, combo):
                if value is not None:
                    params[label] = value
            self.experiments.append(
                ExperimentSpec(
                    tool_name=self.tool_name,
                    parameters=params,
                    objective=self.objective,
                )
            )
        self.total = len(self.experiments)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "objective": self.objective,
            "base_parameters": self.base_parameters,
            "sweep_dims": [
                {
                    "name": d.name,
                    "values": d.values,
                    "min": d.min,
                    "max": d.max,
                    "steps": d.steps,
                }
                for d in self.sweep_dims
            ],
            "total": self.total,
        }


def plan_from_schema(
    schema: dict[str, Any],
    tool_name: str,
    objective: str = "",
    base_parameters: dict[str, Any] | None = None,
    max_experiments: int = 64,
) -> ExperimentPlan:
    """Build an ExperimentPlan from a JSON-Schema style spec.

    Schema format (compact):
    {
      "objective": "maximize throughput",
      "sweep": {
        "batch_size": {"values": [4, 8, 16, 32]},
        "learning_rate": {"min": 0.1, "max": 1.0, "steps": 5}
      },
      "base": {"epochs": 10}      # fixed parameters
    }
    """
    base_parameters = dict(base_parameters or {})
    base_parameters.update(schema.get("base", {}))
    objective = schema.get("objective", objective)
    sweep_spec = schema.get("sweep", {})
    dims: list[ParamDim] = []
    for name, dim_spec in sweep_spec.items():
        if isinstance(dim_spec, dict):
            dims.append(ParamDim(
                name=name,
                values=dim_spec.get("values"),
                min=dim_spec.get("min"),
                max=dim_spec.get("max"),
                steps=int(dim_spec.get("steps", 10)),
            ))
        else:
            if isinstance(dim_spec, list):
                dims.append(ParamDim(name=name, values=list(dim_spec)))
            else:
                dims.append(ParamDim(name=name, values=[dim_spec]))

    plan = ExperimentPlan(
        tool_name=tool_name,
        objective=objective,
        base_parameters=base_parameters,
        sweep_dims=dims,
    ).build()

    if plan.total > max_experiments:
        # Cap by trimming axes proportionally (keep the head of each axis).
        cap_ratio = (max_experiments / plan.total) if plan.total else 1.0
        trimmed: list[ParamDim] = []
        for dim in dims:
            n = max(1, math.ceil(len(dim.grid_values()) * cap_ratio))
            dim = ParamDim(
                name=dim.name,
                values=(dim.values[:n] if dim.values else None),
                min=dim.min,
                max=dim.max,
                steps=n,
            )
            trimmed.append(dim)
        plan = ExperimentPlan(
            tool_name=tool_name,
            objective=objective,
            base_parameters=base_parameters,
            sweep_dims=trimmed,
        ).build()

    return plan


def plan_to_json(plan: ExperimentPlan) -> str:
    """Serialize a plan for ledger persistence."""
    return json.dumps(plan.to_dict(), ensure_ascii=False, default=str)