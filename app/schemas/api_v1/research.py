"""Research report API schemas (zero-key web research)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """Body for a research query."""

    query: str
    sources: int = Field(default=3, ge=1, le=8)
    timeout_s: int = Field(default=30, ge=1, le=120)


class Finding(BaseModel):
    """A single scored research finding from one source."""

    source: str
    title: str
    key_points: list[str] = Field(default_factory=list)
    rel_score: float = 0.0


class ResearchResult(BaseModel):
    """Structured output of a research run."""

    ok: bool = False
    query: str = ""
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    generated_at: str = ""
