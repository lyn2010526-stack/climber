"""Notification endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth_manager import require_admin

router = APIRouter()

logger = structlog.get_logger(__name__)


class NotifyRequest(BaseModel):
    title: str
    message: str
    urgency: str = "normal"


@router.post("/send")
@router.post("send")
async def send_notification(
    payload: NotifyRequest,
    _auth: dict[str, Any] = Depends(require_admin()),
) -> dict[str, Any]:
    try:
        from app.main import app

        service = app.state.notification_service
        ok = await service.send(payload.title, payload.message, urgency=payload.urgency)
        return {"ok": ok}
    except Exception as exc:
        logger.warning("notification_send_failed", urgency=payload.urgency, error=str(exc))
        return {"ok": False, "error": "通知发送失败"}


@router.get("/test")
@router.get("test")
async def test_notification() -> dict[str, Any]:
    try:
        from app.main import app

        service = app.state.notification_service
        ok = await service.send("Climber", "通知系统测试成功")
        return {"ok": ok}
    except Exception as exc:
        logger.warning("notification_test_failed", error=str(exc))
        return {"ok": False, "error": "通知发送失败"}
