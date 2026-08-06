"""Cost and usage API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.v1.common import current_user_id
from app.api.v1.helpers import DEFAULT_USER
from app.storage import async_session
from app.storage.models_cost import BudgetConfig, CostRecord, UsageQuota

router = APIRouter()


def _cost_dict(c: CostRecord) -> dict[str, Any]:
    return {"id": c.id, "provider": c.provider, "model_id": c.model_id, "prompt_tokens": c.prompt_tokens, "completion_tokens": c.completion_tokens, "total_tokens": c.total_tokens, "input_cost": c.input_cost, "output_cost": c.output_cost, "total_cost": c.total_cost, "created_at": c.created_at.isoformat() if c.created_at else ""}


@router.get("/cost/records")
@router.get("/cost/records/")
async def list_cost_records(session_id: str = "") -> list[dict[str, Any]]:
    async with async_session() as db:
        stmt = select(CostRecord).order_by(CostRecord.created_at.desc())
        if session_id:
            stmt = stmt.where(CostRecord.session_id == session_id)
        rows = (await db.execute(stmt)).scalars().all()
        return [_cost_dict(c) for c in rows]


@router.get("/cost/budget")
@router.get("/cost/budget/")
async def get_budget() -> dict[str, Any]:
    async with async_session() as db:
        cfg = (await db.execute(select(BudgetConfig).where(BudgetConfig.user_id == DEFAULT_USER))).scalars().first()
        if cfg is None:
            cfg = BudgetConfig(user_id=DEFAULT_USER)
            db.add(cfg)
            await db.commit()
            await db.refresh(cfg)
        return {"amount": cfg.amount, "period": cfg.period, "is_active": cfg.is_active, "per_session_limit": cfg.per_session_limit, "per_request_limit": cfg.per_request_limit}


@router.get("/cost/quota")
@router.get("/cost/quota/")
async def get_quota() -> dict[str, Any]:
    async with async_session() as db:
        q = (await db.execute(select(UsageQuota).where(UsageQuota.user_id == DEFAULT_USER))).scalars().first()
        if q is None:
            q = UsageQuota(user_id=DEFAULT_USER)
            db.add(q)
            await db.commit()
            await db.refresh(q)
        return {"max_requests_per_day": q.max_requests_per_day, "max_tokens_per_day": q.max_tokens_per_day, "max_cost_per_month": q.max_cost_per_month, "requests_today": q.requests_today, "tokens_today": q.tokens_today, "cost_this_month": q.cost_this_month}


@router.get("/cost/usage")
@router.get("/cost/usage/")
async def get_cost_usage(request: Request) -> dict[str, Any]:
    async with async_session() as db:
        user_id = current_user_id(request)
        stmt = select(func.sum(CostRecord.total_cost), func.sum(CostRecord.total_tokens), func.count(CostRecord.id)).where(CostRecord.user_id == user_id)
        row = (await db.execute(stmt)).one()
        total_cost = row[0] or 0
        total_tokens = row[1] or 0
        total_calls = row[2] or 0
        return {
            "total_cost": round(float(total_cost), 6),
            "total_tokens": int(total_tokens),
            "total_calls": int(total_calls),
            "by_model": [],
            "by_day": [],
        }
