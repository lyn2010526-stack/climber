"""Evaluation task definition (research-100 P1: inspect_ai / promptfoo fusion).

A task bundles a prompt with an optional reference answer and explicit,
deterministic check functions. Checks are the grader: they decide pass/fail
without any model grading, so recorded scores are never fabricated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class Check(Protocol):
    """Deterministic pass/fail assertion over a run result."""

    def __call__(self, output: str, reference: str | None) -> bool:
        ...


def contains(needle: str) -> Check:
    """True when the agent's final answer contains `needle` (case-sensitive)."""

    def check(output: str, reference: str | None) -> bool:  # task check() interface: reference is part of the contract
        return needle in output

    return check


def equals_any(variants: tuple[str, ...]) -> Check:
    """True when the final answer equals one of the given variants after trimming."""

    def check(output: str, reference: str | None) -> bool:  # task check() interface: reference is part of the contract
        normalized = output.strip()
        return any(normalized == variant.strip() for variant in variants)

    return check


def file_matches(workspace: Path, relative: str, expected: str) -> Check:
    """True when the workspace file `relative` decodes to exactly `expected`."""

    def check(output: str, reference: str | None) -> bool:  # task check() interface: output/reference are part of the contract
        target = (workspace / relative).resolve()
        if not target.is_relative_to(workspace.resolve()):
            return False
        try:
            return target.read_text(encoding="utf-8") == expected
        except (OSError, UnicodeDecodeError):
            return False

    return check


def load_eval_task(path: str | Path) -> EvalTask:
    """Load an eval task from a UTF-8 file.

    Accepts a JSON object with the fields {id, prompt} plus an optional
    `reference` string. Plain text files yield a task without a reference and
    with no default checks (caller supplies them).
    """
    path = Path(path)
    with path.open("rb") as stream:
        raw = stream.read(262145)
    if len(raw) > 262144:
        raise ValueError("Task exceeds byte limit")
    text = raw.decode("utf-8")
    if path.suffix.lower() != ".json":
        return EvalTask(id=path.stem, prompt=text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("JSON eval task must be an object")
    if set(payload) - {"id", "prompt", "reference"}:
        raise ValueError("Eval task may only carry id, prompt and reference")
    prompt = payload.get("prompt")
    task_id = payload.get("id", path.stem)
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("Task prompt must be nonempty text")
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("Task id must be nonempty text")
    reference = payload.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise ValueError("Task reference must be text")
    return EvalTask(id=task_id, prompt=prompt, reference=reference)


@dataclass
class EvalTask:
    id: str
    prompt: str
    reference: str | None = None
    checks: list[Check] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id or not self.prompt:
            raise ValueError("EvalTask requires a nonempty id and prompt")
        if not isinstance(self.checks, list):
            raise ValueError("EvalTask checks must be a list of callables")
