"""Behavior contracts for skills added from the deep-dive research."""

import pytest

from app.skills.builtins import skill_delegation_packet, skill_typed_memory_recall


@pytest.mark.asyncio
async def test_delegation_packet_contains_scope_and_evidence_fields() -> None:
    result = await skill_delegation_packet(
        "Implement the parser",
        allowed_paths="app/parser.py",
        acceptance_criteria="focused pytest passes",
    )
    assert "Implement the parser" in result
    assert "app/parser.py" in result
    assert "Acceptance criteria" in result
    assert "raw errors" in result


@pytest.mark.asyncio
async def test_typed_memory_recall_preserves_log_plan_and_metadata() -> None:
    result = await skill_typed_memory_recall("parser failures", kind="anti_pattern", phase="plan")
    assert "anti_pattern" in result
    assert "PLAN phase" in result
    assert "confidence" in result
    assert "timestamp" in result
