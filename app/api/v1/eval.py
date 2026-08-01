"""Evaluation API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.v1.helpers import DEFAULT_USER, payload as _payload
from app.storage import async_session
from app.storage.models_eval import EvalDataset, EvalRun

router = APIRouter()


def _eval_dataset_dict(e: EvalDataset) -> dict[str, Any]:
    return {"id": e.id, "name": e.name, "description": e.description, "case_count": e.case_count, "created_at": e.created_at.isoformat() if e.created_at else ""}


def _eval_run_dict(r: EvalRun) -> dict[str, Any]:
    return {"id": r.id, "dataset_id": r.dataset_id, "agent_id": r.agent_id, "total_cases": r.total_cases, "passed_cases": r.passed_cases, "failed_cases": r.failed_cases, "pass_rate": r.pass_rate, "average_score": r.average_score, "created_at": r.created_at.isoformat() if r.created_at else ""}


@router.get("/eval/datasets")
@router.get("/eval/datasets/")
async def list_eval_datasets() -> list[dict[str, Any]]:
    async with async_session() as db:
        rows = (await db.execute(select(EvalDataset).order_by(EvalDataset.created_at.desc()))).scalars().all()
        return [_eval_dataset_dict(e) for e in rows]


@router.post("/eval/datasets")
@router.post("/eval/datasets/")
async def create_eval_dataset(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        ds = EvalDataset(user_id=DEFAULT_USER, name=data.get("name", "New Dataset"), description=data.get("description", ""), data_json=data.get("data_json", "[]"))
        db.add(ds)
        await db.commit()
        await db.refresh(ds)
        return _eval_dataset_dict(ds)


@router.post("/eval/run")
@router.post("/eval/run/")
async def run_evaluation(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        run = EvalRun(user_id=DEFAULT_USER, dataset_id=data.get("dataset_id", ""), agent_id=data.get("agent_id", ""), total_cases=int(data.get("total_cases") or 0), passed_cases=int(data.get("passed_cases") or 0), failed_cases=int(data.get("failed_cases") or 0), average_score=float(data.get("average_score") or 0.0), pass_rate=float(data.get("pass_rate") or 0.0), results_json=data.get("results_json", "[]"))
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _eval_run_dict(run)