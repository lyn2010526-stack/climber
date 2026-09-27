"""Errors raised by the evaluation runtime.

These are operational errors (bad request, unknown target, unusable target
setup). They are deliberately distinct from *measurement* outcomes: a target
that legitimately cannot be measured reports
:data:`~app.eval.types.Verdict.INCONCLUSIVE` with a reason rather than raising.
"""

from __future__ import annotations


class EvaluationError(Exception):
    """Base class for evaluation runtime errors."""


class TargetNotFoundError(EvaluationError):
    """No evaluation target is registered under the requested name."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = sorted(available)
        super().__init__(
            f"unknown evaluation target {name!r}; registered targets: "
            f"{', '.join(self.available) if self.available else '<none>'}"
        )


class TargetSetupError(EvaluationError):
    """A target could not be constructed from the supplied specification."""
