"""API tests for the offline evaluation endpoints.

`POST /eval/assess` reuses the core deterministic judge so it must be fully
offline and reproducible; `GET /eval/reports` reads the in-memory report store.
"""

from __future__ import annotations

import pytest

from app.core.evaluation.models import EvaluationReport
from app.core.evaluation.report_store import REPORT_STORE


@pytest.mark.asyncio
async def test_assess_passes_when_keywords_present(client) -> None:
    response = await client.post(
        "/api/v1/eval/assess",
        json={
            "output": "已完成任务评估，输出包含 summary 和 result 关键字。",
            "rubric": [
                {
                    "item_id": "summary",
                    "description": "输出包含总结",
                    "contains_any": ["summary"],
                    "weight": 1.0,
                    "essential": True,
                },
                {
                    "item_id": "result",
                    "description": "输出包含结果",
                    "contains_any": ["result"],
                    "weight": 1.0,
                },
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["judge"] == "deterministic"
    assert body["passed"] is True
    assert body["score"] == 1.0
    assert {v["item_id"] for v in body["verdicts"]} == {"summary", "result"}
    assert all(v["passed"] for v in body["verdicts"])


@pytest.mark.asyncio
async def test_assess_fails_when_keywords_missing(client) -> None:
    response = await client.post(
        "/api/v1/eval/assess",
        json={
            "output": "没有任何期望内容。",
            "rubric": [
                {
                    "item_id": "keyword",
                    "description": "必须包含关键词",
                    "contains_any": ["must-have-term"],
                    "essential": True,
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passed"] is False
    assert body["score"] == 0.0
    assert body["failure_reasons"], "essential failure must produce a reason"


@pytest.mark.asyncio
async def test_assess_veto_zeroes_score(client) -> None:
    response = await client.post(
        "/api/v1/eval/assess",
        json={
            "output": "输出包含 secret 但不应出现。",
            "rubric": [
                {
                    "item_id": "no-secret",
                    "description": "不得包含敏感词",
                    "not_contains_any": ["secret"],
                    "veto": True,
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["passed"] is False
    assert body["score"] == 0.0


@pytest.mark.asyncio
async def test_assess_rejects_empty_output_and_rubric(client) -> None:
    assert (
        await client.post("/api/v1/eval/assess", json={"output": "  ", "rubric": []})
    ).status_code == 422
    assert (
        await client.post("/api/v1/eval/assess", json={"output": "some text", "rubric": []})
    ).status_code == 422


@pytest.mark.asyncio
async def test_reports_list_and_detail_roundtrip(client) -> None:
    REPORT_STORE.clear()
    report = EvaluationReport(
        total_scenarios=2,
        passed_scenarios=1,
        average_score=0.5,
        pass_at_k={"k1": 0.5},
    )
    REPORT_STORE.save(report)

    listed = await client.get("/api/v1/eval/reports")
    assert listed.status_code == 200, listed.text
    summaries = listed.json()
    assert summaries and summaries[0]["report_id"] == report.report_id
    assert summaries[0]["total_scenarios"] == 2
    assert summaries[0]["passed_scenarios"] == 1

    detail = await client.get(f"/api/v1/eval/reports/{report.report_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["report_id"] == report.report_id
    assert detail.json()["scenarios"] == []


@pytest.mark.asyncio
async def test_reports_missing_id_404(client) -> None:
    response = await client.get("/api/v1/eval/reports/no-such-report")
    assert response.status_code == 404
