"""Evaluation dataset and run endpoints.

Split out of the former monolithic generic API module (pure move refactor).
Routes are registered with and without a trailing slash because the app runs
with redirect_slashes=False.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.api.v1._shared import DEFAULT_USER, _payload
from app.core.auth import get_current_user
from app.storage import async_session
from app.storage.models_eval import EvalDataset, EvalRun

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = structlog.get_logger()

# ─── Eval ───────────────────────────────────────────────────────────────────



def _eval_dataset_dict(e: EvalDataset) -> dict[str, Any]:
    return {
        "id": e.id,
        "name": e.name,
        "description": e.description,
        "case_count": e.case_count,
        "created_at": e.created_at.isoformat() if e.created_at else "",
    }


def _eval_run_dict(r: EvalRun) -> dict[str, Any]:
    return {
        "id": r.id,
        "dataset_id": r.dataset_id,
        "agent_id": r.agent_id,
        "total_cases": r.total_cases,
        "passed_cases": r.passed_cases,
        "failed_cases": r.failed_cases,
        "pass_rate": r.pass_rate,
        "average_score": r.average_score,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }


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
        ds = EvalDataset(
            user_id=DEFAULT_USER,
            name=data.get("name", "New Dataset"),
            description=data.get("description", ""),
            data_json=data.get("data_json", "[]"),
        )
        db.add(ds)
        await db.commit()
        await db.refresh(ds)
        return _eval_dataset_dict(ds)


@router.post("/eval/run")
@router.post("/eval/run/")
async def run_evaluation(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    async with async_session() as db:
        run = EvalRun(
            user_id=DEFAULT_USER,
            dataset_id=data.get("dataset_id", ""),
            agent_id=data.get("agent_id", ""),
            total_cases=int(data.get("total_cases") or 0),
            passed_cases=int(data.get("passed_cases") or 0),
            failed_cases=int(data.get("failed_cases") or 0),
            average_score=float(data.get("average_score") or 0.0),
            pass_rate=float(data.get("pass_rate") or 0.0),
            results_json=data.get("results_json", "[]"),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _eval_run_dict(run)


_BUILTIN_EVAL_DATASETS = [
    {
        "name": "general-knowledge",
        "description": "General knowledge Q&A benchmark with factual questions.",
        "cases": [
            {"question": "What is the capital of France?", "expected": "Paris"},
            {"question": "How many planets are in our solar system?", "expected": "8"},
            {"question": "Who wrote Romeo and Juliet?", "expected": "Shakespeare"},
            {"question": "What is the chemical symbol for water?", "expected": "H2O"},
            {"question": "Which ocean is the largest?", "expected": "Pacific"},
        ],
    },
    {
        "name": "reasoning",
        "description": "Logical reasoning and multi-step problem solving benchmark.",
        "cases": [
            {"question": "If all A are B and all B are C, then are all A also C?", "expected": "yes"},
            {"question": "A train leaves at 10:30 and arrives at 14:45. How long is the journey?", "expected": "4 hours 15 minutes"},
            {"question": "Three consecutive integers sum to 24. What is the smallest?", "expected": "7"},
        ],
    },
    {
        "name": "tool-usage",
        "description": "Benchmark for correct tool selection and invocation.",
        "cases": [
            {"question": "Find the current time on the server.", "expected": "tool:get_current_time"},
            {"question": "Search the web for the latest news about AI.", "expected": "tool:web_search"},
            {"question": "Calculate 42 * 17 using a calculator.", "expected": "tool:calculator"},
        ],
    },
]


@router.post("/eval/datasets/seed-builtin")
@router.post("/eval/datasets/seed-builtin/")
async def seed_builtin_eval_datasets() -> dict[str, Any]:
    """Seed the built-in evaluation datasets (idempotent by name)."""
    async with async_session() as db:
        existing_names = set(
            (await db.execute(select(EvalDataset.name))).scalars().all()
        )
        added: list[EvalDataset] = []
        for spec in _BUILTIN_EVAL_DATASETS:
            if spec["name"] in existing_names:
                continue
            ds = EvalDataset(
                user_id=DEFAULT_USER,
                name=spec["name"],
                description=spec["description"],
                data_json=json.dumps(spec["cases"], ensure_ascii=False),
                case_count=len(spec["cases"]),
            )
            db.add(ds)
            added.append(ds)
        await db.commit()
        for ds in added:
            await db.refresh(ds)
        return {"ok": True, "created": len(added), "datasets": [_eval_dataset_dict(ds) for ds in added]}


@router.post("/eval/datasets/{dataset_id}/run")
@router.post("/eval/datasets/{dataset_id}/run/")
async def run_eval_dataset(dataset_id: str) -> dict[str, Any]:
    """Run an evaluation against an existing dataset (reuses /eval/run logic)."""
    from app.storage.database import Agent

    async with async_session() as db:
        ds = (await db.execute(select(EvalDataset).where(EvalDataset.id == dataset_id))).scalar_one_or_none()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found")
        agent = (await db.execute(
            select(Agent).where(Agent.user_id == DEFAULT_USER).order_by(Agent.created_at.asc())
        )).scalars().first()
        if not agent:
            agent = (await db.execute(select(Agent).order_by(Agent.created_at.asc()))).scalars().first()
        if not agent:
            raise HTTPException(status_code=400, detail="No agent available to run evaluation")
        run = EvalRun(
            user_id=DEFAULT_USER,
            dataset_id=dataset_id,
            agent_id=agent.id,
            total_cases=ds.case_count,
            passed_cases=0,
            failed_cases=0,
            average_score=0.0,
            pass_rate=0.0,
            results_json="[]",
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return _eval_run_dict(run)
