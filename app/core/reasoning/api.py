"""Reasoning API — multi-strategy reasoning endpoint with streaming support."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_engine import AgentEngine
from app.core.reasoning import (
    ReasoningFeedback,
    ReasoningRequest,
    ReasoningResult,
)
from app.storage import get_db
from app.storage.repository_reasoning import (
    ReasoningTraceRepository,
    ReasoningFeedbackRepository,
)
from app.middleware.rate_limit import RateLimit

DEFAULT_USER = "default-user"

router = APIRouter(tags=["reasoning"], redirect_slashes=False)


@router.post("/")
async def reason_with_slash(
    request: ReasoningRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = RateLimit,
) -> ReasoningResult:
    from app.api.v1 import get_engine

    engine = get_engine()
    if not engine.reasoning or not engine.reasoning.is_available():
        raise HTTPException(status_code=503, detail="Reasoning engine not initialized")

    try:
        result = await engine.reasoning.pipeline.reason(request)

        if result.trace:
            trace_repo = ReasoningTraceRepository(db)
            await trace_repo.create({
                "trace_id": result.trace.trace_id,
                "user_id": DEFAULT_USER,
                "task": result.trace.task,
                "mode": result.mode_used.value,
                "candidates_count": len(result.candidates),
                "best_confidence": max((c.confidence for c in result.candidates), default=0.0),
                "coverage_score": result.coverage.score if result.coverage else None,
                "duration_ms": result.total_duration_ms,
                "total_tokens": result.total_tokens,
                "estimated_cost": result.estimated_cost,
                "result_summary": result.answer[:500] if result.answer else None,
                "path_traces": [p.dict() for p in result.trace.path_traces] if result.trace.path_traces else [],
                "coverage_report": result.coverage.dict() if result.coverage else None,
            })

        return result
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")


@router.post("")
async def reason_no_slash(
    request: ReasoningRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = RateLimit,
) -> ReasoningResult:
    return await reason_with_slash(request, db)


@router.post("/stream")
async def reason_stream(
    request: ReasoningRequest,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    from app.api.v1 import get_engine

    engine = get_engine()
    if not engine.reasoning or not engine.reasoning.is_available():
        raise HTTPException(status_code=503, detail="Reasoning engine not initialized")

    async def event_generator():
        yield {"event": "reasoning_start", "data": json.dumps({"mode": request.mode.value, "task": request.task[:100]})}

        try:
            result = await engine.reasoning.pipeline.reason(request)

            if result.trace:
                trace_repo = ReasoningTraceRepository(db)
                await trace_repo.create({
                    "trace_id": result.trace.trace_id,
                    "user_id": DEFAULT_USER,
                    "task": result.trace.task,
                    "mode": result.mode_used.value,
                    "candidates_count": len(result.candidates),
                    "best_confidence": max((c.confidence for c in result.candidates), default=0.0),
                    "coverage_score": result.coverage.score if result.coverage else None,
                    "duration_ms": result.total_duration_ms,
                    "total_tokens": result.total_tokens,
                    "estimated_cost": result.estimated_cost,
                    "result_summary": result.answer[:500] if result.answer else None,
                    "path_traces": [p.dict() for p in result.trace.path_traces] if result.trace.path_traces else [],
                    "coverage_report": result.coverage.dict() if result.coverage else None,
                })

                for path in result.trace.path_traces:
                    yield {"event": "path_complete", "data": json.dumps({
                        "candidate_id": path.candidate_id,
                        "path_type": path.path_type,
                        "confidence": path.final_confidence,
                        "rounds": len(path.rounds),
                    })}

            if result.coverage:
                yield {"event": "coverage", "data": json.dumps({
                    "score": result.coverage.score,
                    "edge_cases": len(result.coverage.edge_cases),
                    "risks": len(result.coverage.risks),
                    "high_risks": len(result.coverage.high_risks),
                })}

            yield {"event": "reasoning_complete", "data": json.dumps({
                "answer": result.answer,
                "mode_used": result.mode_used.value,
                "candidates_count": len(result.candidates),
                "duration_ms": result.total_duration_ms,
                "trace_id": result.trace.trace_id if result.trace else None,
            })}
        except Exception as e:
            yield {"event": "reasoning_error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("/{trace_id}")
async def get_reasoning_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | None:
    repo = ReasoningTraceRepository(db)
    trace = await repo.get_by_trace_id(trace_id)
    if not trace:
        return None
    return {
        "trace_id": trace.trace_id,
        "task": trace.task,
        "mode": trace.mode,
        "candidates_count": trace.candidates_count,
        "best_confidence": trace.best_confidence,
        "coverage_score": trace.coverage_score,
        "duration_ms": trace.duration_ms,
        "total_tokens": trace.total_tokens,
        "estimated_cost": trace.estimated_cost,
        "result_summary": trace.result_summary,
        "path_traces": trace.path_traces,
        "coverage_report": trace.coverage_report,
        "created_at": trace.created_at.isoformat() if trace.created_at else None,
    }


@router.get("/modes")
async def list_reasoning_modes() -> list[dict[str, str]]:
    modes = [
        {"id": "auto", "name": "Auto", "description": "Automatically select best strategy", "available": True},
        {"id": "tree", "name": "Tree of Thought", "description": "Parallel multi-path + self-refine", "available": True},
        {"id": "deep", "name": "Deep Refine", "description": "Iterative refinement with backtracking", "available": True},
        {"id": "debate", "name": "Debate", "description": "Multi-agent debate convergence", "available": True},
    ]
    return modes


@router.post("/{trace_id}/feedback")
async def submit_feedback(
    trace_id: str,
    feedback: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = RateLimit,
) -> dict[str, str]:
    trace_repo = ReasoningTraceRepository(db)
    trace = await trace_repo.get_by_trace_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    feedback_repo = ReasoningFeedbackRepository(db)
    await feedback_repo.create({
        "trace_id": trace_id,
        "user_id": DEFAULT_USER,
        "rating": feedback.get("rating", 3),
        "thumbs": feedback.get("thumbs"),
        "comment": feedback.get("comment", ""),
        "selected_candidate_id": feedback.get("selected_candidate_id"),
    })

    return {"status": "ok", "message": "Feedback recorded"}


@router.get("/{trace_id}/feedback")
async def get_feedback(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = RateLimit,
) -> list[dict[str, Any]]:
    feedback_repo = ReasoningFeedbackRepository(db)
    entries = await feedback_repo.list_by_trace_id(trace_id)
    return [
        {
            "user_id": e.user_id,
            "rating": e.rating,
            "thumbs": e.thumbs,
            "comment": e.comment,
            "selected_candidate_id": e.selected_candidate_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


@router.get("/history")
async def list_reasoning_history(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[dict[str, Any]]:
    trace_repo = ReasoningTraceRepository(db)
    items = await trace_repo.list_by_user(DEFAULT_USER, limit=limit)
    return [
        {
            "trace_id": t.trace_id,
            "task": t.task,
            "mode": t.mode,
            "candidates": t.candidates_count,
            "best_confidence": t.best_confidence,
            "coverage_score": t.coverage_score,
            "duration_ms": t.duration_ms,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in items
    ]