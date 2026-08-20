"""Notification endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


class NotifyRequest(BaseModel):
    title: str
    message: str
    urgency: str = "normal"


@router.post("/send")
async def send_notification(payload: NotifyRequest) -> dict:
    try:
        from app.main import app
        service = app.state.notification_service
        ok = await service.send(payload.title, payload.message, urgency=payload.urgency)
        return {"ok": ok}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/test")
async def test_notification() -> dict:
    try:
        from app.main import app
        service = app.state.notification_service
        ok = await service.send("Climber", "通知系统测试成功")
        return {"ok": ok}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/history")
@router.get("/")
async def list_notifications(limit: int = 50) -> dict[str, Any]:
    """Return recent notification history (newest first)."""
    try:
        from app.main import app
        service = app.state.notification_service
        items = await service.list_recent(limit=max(1, min(int(limit), 200)))
        return {"notifications": items, "total": len(items)}
    except Exception as exc:
        return {"ok": False, "notifications": [], "error": str(exc)}


@router.delete("/history")
async def clear_notifications() -> dict:
    try:
        from app.main import app
        service = app.state.notification_service
        count = await service.clear()
        return {"ok": True, "cleared": count}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
