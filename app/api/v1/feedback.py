"""Feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import async_session
from app.storage.auth import DEFAULT_USER_ID
from app.storage.models_feedback import Feedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: str = ""
    rating: str | int | None = None
    reason: str | None = None
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    reason: str | None = None
    comment: str | None = None


@router.post("/")
@router.post("")
async def submit_feedback(
    message_id: str = "",
    rating: str = "",
    reason: str | None = None,
    comment: str | None = None,
    payload: FeedbackRequest | None = None,
) -> dict:
    if payload is not None:
        message_id = payload.message_id or message_id
        rating = payload.rating if payload.rating is not None else rating
        reason = payload.reason or reason
        comment = payload.comment or comment
    rating_str = str(rating) if rating is not None else ""
    async with async_session() as db:
        existing = (
            await db.execute(
                __import__("sqlalchemy").select(Feedback).where(
                    Feedback.message_id == message_id,
                    Feedback.user_id == DEFAULT_USER_ID,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.rating = rating_str
            existing.reason = reason
            existing.comment = comment
            await db.commit()
            return {"ok": True, "id": existing.id}
        fb = Feedback(
            user_id=DEFAULT_USER_ID,
            message_id=message_id,
            rating=rating_str,
            reason=reason,
            comment=comment,
        )
        db.add(fb)
        await db.commit()
        await db.refresh(fb)
        return {"ok": True, "id": fb.id}


@router.get("/stats")
@router.get("stats")
async def feedback_stats() -> dict:
    async with async_session() as db:
        rows = (await db.execute(__import__("sqlalchemy").select(Feedback))).scalars().all()
        total = len(rows)
        up = sum(1 for r in rows if r.rating == "up")
        down = total - up
        reasons: dict[str, int] = {}
        for r in rows:
            if r.reason:
                reasons[r.reason] = reasons.get(r.reason, 0) + 1
        return {
            "total": total,
            "up_count": up,
            "down_count": down,
            "approval_rate": up / total if total else 0,
            "reason_distribution": reasons,
        }


class ReasoningFeedbackRequest(BaseModel):
    rating: str | int | None = None
    thumbs: str | None = None
    comment: str | None = None


class ReasoningFeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    reason: str | None = None
    comment: str | None = None


@router.post("/reason/{trace_id}/feedback")
@router.post("reason/{trace_id}/feedback")
async def submit_reasoning_feedback(trace_id: str, payload: ReasoningFeedbackRequest) -> dict:
    rating = payload.thumbs or (str(payload.rating) if payload.rating is not None else "")
    message_id = f"reason:{trace_id}"
    async with async_session() as db:
        existing = (
            await db.execute(
                __import__("sqlalchemy").select(Feedback).where(
                    Feedback.message_id == message_id,
                    Feedback.user_id == DEFAULT_USER_ID,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.rating = str(rating)
            existing.reason = payload.comment
            existing.comment = payload.comment
            await db.commit()
            return {"ok": True, "id": existing.id}
        fb = Feedback(
            user_id=DEFAULT_USER_ID,
            message_id=message_id,
            rating=str(rating),
            reason=payload.comment,
            comment=payload.comment,
        )
        db.add(fb)
        await db.commit()
        await db.refresh(fb)
        return {"ok": True, "id": fb.id}


@router.get("/reason/{trace_id}/feedback")
@router.get("reason/{trace_id}/feedback")
async def get_reasoning_feedback(trace_id: str) -> list[dict]:
    message_id = f"reason:{trace_id}"
    async with async_session() as db:
        rows = (
            await db.execute(
                __import__("sqlalchemy").select(Feedback).where(
                    Feedback.message_id == message_id,
                    Feedback.user_id == DEFAULT_USER_ID,
                )
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "message_id": r.message_id,
                "rating": r.rating,
                "reason": r.reason,
                "comment": r.comment,
            }
            for r in rows
        ]
