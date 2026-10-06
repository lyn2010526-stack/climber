"""Cost and usage API endpoints.

Dead-code cleanup (2026-10-05): the ``/cost/records``, ``/cost/budget`` and
``/cost/quota`` handlers were never mounted — ``app/api/v1/__init__.py`` only
extracts the ``/cost/usage`` prefix from this router — and the live versions
of those endpoints exist in ``app/api/v1/routes/misc.py``.  They were removed
per ``docs/audits/dead-code-scan.md``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.v1.common import current_user_id
from app.storage import async_session
from app.storage.models_cost import CostRecord

router = APIRouter()


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
