"""The evaluation target contract and its registry.

A *target* is the thing being evaluated. It owns exactly one job: run something
real and report what it measured. The runtime around it never invents a number,
so a target that cannot measure honestly reports
:data:`~app.eval.types.Verdict.INCONCLUSIVE` with a reason.

Adding a target means implementing :class:`EvalTarget` and registering it; no
other module in :mod:`app.eval` needs to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.eval.errors import TargetNotFoundError, TargetSetupError
from app.eval.types import TargetRunResult

TARGET_ARCBENCH = "arcbench"


@dataclass(frozen=True)
class TargetSpec:
    """Everything needed to identify and execute one target run.

    ``config`` is free-form and owned by the target. ``expected_cases`` is the
    authoritative count of what must be measured; it is what lets the runtime
    detect coverage gaps, so a target that silently measures nothing is caught
    instead of reported as a clean pass.
    """

    target: str
    spec: dict[str, Any]
    config: dict[str, Any] = field(default_factory=dict)
    expected_cases: int = 0
    workdir: str = ""

    def __post_init__(self) -> None:
        if not str(self.target or "").strip():
            raise TargetSetupError("target name is required")
        if not isinstance(self.spec, dict):
            raise TargetSetupError("spec must be an object")
        if not isinstance(self.config, dict):
            raise TargetSetupError("config must be an object")
        if self.expected_cases < 0:
            raise TargetSetupError("expected_cases must not be negative")

    def config_value(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def describe(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "spec": dict(self.spec),
            "config": dict(self.config),
            "expected_cases": self.expected_cases,
        }


class EvalTarget(ABC):
    """A registered evaluation target.

    ``preflight`` reports which capabilities are present *before* anything runs.
    Blocking checks let the runtime refuse to attribute an outcome when the
    infrastructure is absent, which is what keeps a missing browser or a missing
    report from being recorded as a test failure.
    """

    name: str = ""
    description: str = ""

    def build(self, spec: TargetSpec) -> Any:
        """Return the target-specific execution plan for ``spec``."""
        raise NotImplementedError

    def preflight(self, spec: TargetSpec) -> list[Any]:
        """Return capability checks for this run. Empty means nothing to check."""
        return []

    @abstractmethod
    def execute(self, spec: TargetSpec) -> TargetRunResult:
        """Run the target for real and report what it measured."""


_REGISTRY: dict[str, EvalTarget] = {}


def register(target: EvalTarget) -> EvalTarget:
    """Register ``target`` under its declared name."""
    name = str(target.name or "").strip()
    if not name:
        raise TargetSetupError("target.name is required for registration")
    _REGISTRY[name] = target
    return target


def get_target(name: str) -> EvalTarget:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise TargetNotFoundError(name, list(_REGISTRY)) from exc


def registered_targets() -> list[EvalTarget]:
    return [_REGISTRY[name] for name in sorted(_REGISTRY)]


def unregister(name: str) -> None:
    """Remove a target from the registry.

    Exists so a test or a plugin can install a temporary target without leaking
    it into the process-wide registry.
    """
    _REGISTRY.pop(name, None)


def describe_targets() -> list[dict[str, str]]:
    return [
        {"name": target.name, "description": target.description}
        for target in registered_targets()
    ]
