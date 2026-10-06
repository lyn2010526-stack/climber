"""Contracts for the round-2 discipline skills.

Covers five enhancement dimensions synthesized from the deep-dive references:
execution (anti-laziness / anti-overreach), tool-call constraints, progress
reporting, thinking budget, and evidence chain. Each skill must be declared,
registered, and return the expected contract text.
"""

from __future__ import annotations

import pytest

from app.skills.builtins import (
    skill_evidence_chain_discipline,
    skill_execution_discipline,
    skill_progress_report_discipline,
    skill_thinking_budget_discipline,
    skill_tool_call_discipline,
)
from app.skills.definitions import (
    BUILTIN_HANDLER_MAP,
    BUILTIN_SKILLS,
    register_builtin_skills,
)
from app.skills.registry import SkillCategory, SkillRegistry

NEW_DISCIPLINE_IDS = (
    "execution_discipline",
    "tool_call_discipline",
    "progress_report_discipline",
    "thinking_budget_discipline",
    "evidence_chain_discipline",
)


def test_new_disciplines_are_declared_with_tags_and_prompts() -> None:
    by_id = {info.id: info for info in BUILTIN_SKILLS}
    for skill_id in NEW_DISCIPLINE_IDS:
        assert skill_id in by_id, skill_id
        info = by_id[skill_id]
        assert info.category is SkillCategory.QUALITY
        assert info.system_prompt
        assert info.tags

    assert "quality" in by_id["execution_discipline"].tags
    assert "scope" in by_id["execution_discipline"].tags
    assert {"tools", "tool-call"} <= set(by_id["tool_call_discipline"].tags)
    assert {"progress", "reporting"} <= set(by_id["progress_report_discipline"].tags)
    assert {"thinking", "reasoning"} <= set(by_id["thinking_budget_discipline"].tags)
    assert {"evidence", "verification"} <= set(by_id["evidence_chain_discipline"].tags)


def test_new_disciplines_have_handlers_and_register() -> None:
    assert set(NEW_DISCIPLINE_IDS) <= set(BUILTIN_HANDLER_MAP)
    registry = SkillRegistry()
    register_builtin_skills(registry)
    for skill_id in NEW_DISCIPLINE_IDS:
        assert registry.get(skill_id) is not None
        assert registry.get_handler(skill_id) is BUILTIN_HANDLER_MAP[skill_id]


@pytest.mark.asyncio
async def test_execution_discipline_covers_anti_laziness_and_scope() -> None:
    result = await skill_execution_discipline("修改登录入口")
    assert "修改登录入口" in result
    assert "偷懒式假完成" in result
    assert "过早放弃" in result
    assert "假成功" in result
    assert "最小可解集" in result


@pytest.mark.asyncio
async def test_tool_call_discipline_covers_boundaries_and_ordering() -> None:
    result = await skill_tool_call_discipline()
    assert "工具边界" in result
    assert "并行" in result
    assert "串行" in result
    assert "编造工具结果" in result
    assert "连续失败约 3 次" in result


@pytest.mark.asyncio
async def test_progress_report_discipline_covers_verifiable_events() -> None:
    result = await skill_progress_report_discipline()
    assert "phase" in result
    assert "next_step" in result
    assert "UNVERIFIED" in result
    assert "不能批准自己的" in result


@pytest.mark.asyncio
async def test_thinking_budget_discipline_matches_depth_to_difficulty() -> None:
    result = await skill_thinking_budget_discipline()
    assert "思考等级" in result
    assert "decision complete" in result
    assert "编造数据" in result


@pytest.mark.asyncio
async def test_evidence_chain_discipline_requires_independent_review() -> None:
    result = await skill_evidence_chain_discipline()
    assert "独立证据" in result
    assert "自我批准" in result
    assert "置信度" in result
