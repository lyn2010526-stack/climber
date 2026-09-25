"""Data models for the simulation experiment harness.

Maps directly to the loop described by the science-agent references:
an experiment plan produces candidate parameter sets, each is dispatched
to an external simulation/MCP tool, the returned output is probed for
convergence, a reviewer accepts or rejects the result, and rejected
parameters are adjusted for the next round. The full lifecycle is
persisted to a ledger for reproducibility.
"""

from __future__ import annotations

import time
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RETRY = "retry"


class ProbeResult(BaseModel):
    """Outcome of running convergence/plausibility probes on tool output."""
    ok: bool = False
    reason: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)


class ExperimentSpec(BaseModel):
    """One experiment: a tool call with a specific parameter set."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tool_name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    objective: str = ""  # metric name and target, e.g. "maximize throughput"


class ExperimentAttempt(BaseModel):
    """A single dispatch of an experiment spec to the tool."""
    round: int
    spec_id: str
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    output: str = ""
    success: bool = False
    error: str = ""
    duration_ms: float = 0.0
    probe: ProbeResult = Field(default_factory=ProbeResult)
    verdict: Verdict | None = None
    reviewer_note: str = ""
    timestamp: float = Field(default_factory=time.time)


class ExperimentReport(BaseModel):
    """Final report for one experiment after all rounds."""
    spec: ExperimentSpec
    attempts: list[ExperimentAttempt] = Field(default_factory=list)
    accepted_attempt: ExperimentAttempt | None = None
    rounds_used: int = 0
    max_rounds: int = 0
