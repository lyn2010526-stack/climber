"""API tests for the read-only instruction understanding endpoint."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_understand_returns_structured_goal(client) -> None:
    response = await client.post(
        "/api/v1/instruction-traces/understand",
        json={"raw_text": "实现一个排序算法，要求复杂度为 O(n log n)。"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["main_goal"]
    assert body["progress"] == "understood"
    assert body["confidence"] > 0
    assert "排序算法" in body["plain_language_summary"]
    assert any("复杂度" in c for c in body["constraints"])


@pytest.mark.asyncio
async def test_understand_flags_pronoun_ambiguity(client) -> None:
    response = await client.post(
        "/api/v1/instruction-traces/understand",
        json={"raw_text": "请重构这个模块。"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["main_goal"]
    assert body["progress"] == "needs_clarification"
    assert body["clarification_questions"]


@pytest.mark.asyncio
async def test_understand_low_confidence_ack(client) -> None:
    response = await client.post(
        "/api/v1/instruction-traces/understand",
        json={"raw_text": "好的"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["main_goal"] is None
    assert body["progress"] == "needs_clarification"
    assert body["clarification_questions"]


@pytest.mark.asyncio
async def test_understand_rejects_blank_text(client) -> None:
    response = await client.post("/api/v1/instruction-traces/understand", json={"raw_text": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_understand_never_leaks_profile_evidence(client) -> None:
    response = await client.post(
        "/api/v1/instruction-traces/understand",
        json={"raw_text": "实现一个排序算法", "context": "performance-critical"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "profile_evidence" not in body
    assert body["candidates"]