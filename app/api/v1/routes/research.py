"""Research API — run a zero-key web research query and return a report."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.api_v1.research import ResearchRequest, ResearchResult
from app.tools.research import run_research

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResult)
def research(req: ResearchRequest) -> ResearchResult:
    """Run an online research pipeline for ``query`` and return a report dict."""
    result = run_research(req.query, sources=req.sources, timeout_s=req.timeout_s)
    return ResearchResult(**result)
