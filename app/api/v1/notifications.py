"""Notification endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class NotifyRequest(BaseModel):
    title: str
    message: str
    urgency: str = "normal"


@router.post("/send")
@router.post("send")
async def send_notification(payload: NotifyRequest) -> dict:
    try:
        from app.main import app
        service = app.state.notification_service
        ok = await service.send(payload.title, payload.message, urgency=payload.urgency)
        return {"ok": ok}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/test")
@router.get("test")
async def test_notification() -> dict:
    try:
        from app.main import app
        service = app.state.notification_service
        ok = await service.send("Climber", "通知系统测试成功")
        return {"ok": ok}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
