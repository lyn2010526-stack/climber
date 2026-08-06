"""Feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.common import current_user_id
from app.storage import async_session
from app.storage.database import Message, Session
from app.storage.models_feedback import Feedback
from app.storage.models_reasoning import ReasoningFeedbackDB, ReasoningTraceDB

DEFAULT_USER_ID = "default-user"

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
    request: Request,
    message_id: str = "",
    rating: str = "",
    reason: str | None = None,
    comment: str | None = None,
    payload: FeedbackRequest | None = None,
) -> dict:
    user_id = current_user_id(request)
    if payload is not None:
        message_id = payload.message_id or message_id
        rating = payload.rating if payload.rating is not None else rating
        reason = payload.reason or reason
        comment = payload.comment or comment
    rating_str = str(rating) if rating is not None else ""
    async with async_session() as db:
        if not message_id:
            raise HTTPException(status_code=422, detail="message_id is required")
        message = (
            await db.execute(
                select(Message)
                .join(Session, Session.id == Message.session_id)
                .where(Message.id == message_id, Session.user_id == user_id)
            )
        ).scalar_one_or_none()
        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")
        existing = (
            await db.execute(
                select(Feedback).where(
                    Feedback.message_id == message_id,
                    Feedback.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.rating = rating_str
            existing.reason = reason
            existing.comment = comment
            try:
                await db.commit()
            except IntegrityError as exc:
                await db.rollback()
                raise HTTPException(status_code=409, detail="Feedback already exists") from exc
            return {"ok": True, "id": existing.id}
        fb = Feedback(
            user_id=user_id,
            message_id=message_id,
            rating=rating_str,
            reason=reason,
            comment=comment,
        )
        db.add(fb)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=422, detail="Feedback references invalid data") from exc
        await db.refresh(fb)
        return {"ok": True, "id": fb.id}


@router.get("/stats")
@router.get("stats")
async def feedback_stats(request: Request) -> dict:
    user_id = current_user_id(request)
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Feedback).where(Feedback.user_id == user_id)
            )
        ).scalars().all()
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
async def submit_reasoning_feedback(trace_id: str, request: Request, payload: ReasoningFeedbackRequest) -> dict:
    user_id = current_user_id(request)
    thumbs = payload.thumbs
    if isinstance(payload.rating, int):
        rating = payload.rating
    else:
        rating = 1 if thumbs == "up" else -1 if thumbs == "down" else 0
    async with async_session() as db:
        trace = (
            await db.execute(
                select(ReasoningTraceDB).where(
                    ReasoningTraceDB.trace_id == trace_id,
                    ReasoningTraceDB.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if trace is None:
            raise HTTPException(status_code=404, detail="Reasoning trace not found")
        existing = (
            await db.execute(
                select(ReasoningFeedbackDB).where(
                    ReasoningFeedbackDB.trace_id == trace_id,
                    ReasoningFeedbackDB.user_id == user_id,
                )
            )
        ).scalars().first()
        if existing is not None:
            existing.rating = rating
            existing.thumbs = thumbs
            existing.comment = payload.comment
            try:
                await db.commit()
            except IntegrityError as exc:
                await db.rollback()
                raise HTTPException(status_code=409, detail="Reasoning feedback conflicts with stored data") from exc
            return {"ok": True, "id": existing.id}
        fb = ReasoningFeedbackDB(
            user_id=user_id,
            trace_id=trace_id,
            rating=rating,
            thumbs=thumbs,
            comment=payload.comment or "",
        )
        db.add(fb)
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise HTTPException(status_code=422, detail="Reasoning feedback references invalid data") from exc
        await db.refresh(fb)
        return {"ok": True, "id": fb.id}


@router.get("/reason/{trace_id}/feedback")
@router.get("reason/{trace_id}/feedback")
async def get_reasoning_feedback(trace_id: str, request: Request) -> list[dict]:
    user_id = current_user_id(request)
    async with async_session() as db:
        rows = (
            await db.execute(
                select(ReasoningFeedbackDB).where(
                    ReasoningFeedbackDB.trace_id == trace_id,
                    ReasoningFeedbackDB.user_id == user_id,
                )
            )
        ).scalars().all()
        return [
            {
                "id": r.id,
                "trace_id": r.trace_id,
                "rating": r.rating,
                "thumbs": r.thumbs,
                "comment": r.comment,
            }
            for r in rows
        ]
