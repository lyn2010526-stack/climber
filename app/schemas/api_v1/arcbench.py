"""ARC-Bench submission status API schemas (read-only)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArcBenchEvent(BaseModel):
    """A single normalized entry from `.arc/runner-events.jsonl`."""

    type: str
    timestamp: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ArcBenchAcceptance(BaseModel):
    """Aggregated acceptance/test outcome for the latest run."""

    ran: bool = False
    passed: int = 0
    failed: int = 0
    unverified: int = 0
    note: str = ""


class ArcBenchStatus(BaseModel):
    """Snapshot of the most recent ARC-Bench run for the competition console."""

    available: bool = False
    message: str = ""
    output_dir: str | None = None
    phase: str = "idle"
    phase_detail: str = ""
    trace_path: str | None = None
    trace_exists: bool = False
    acceptance: ArcBenchAcceptance | None = None
    last_events: list[ArcBenchEvent] = Field(default_factory=list)
    pack_artifact: str | None = None
    pack_exists: bool = False
    updated_at: str | None = None
