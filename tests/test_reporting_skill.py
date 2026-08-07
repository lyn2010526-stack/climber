"""Tests for reporting skill."""

import pytest

from app.skills.reporting_skill import (
    ReportingSkill,
    ReportingSkillContext,
    ReportingSkillRegistry,
)


class TestReportingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ReportingSkill()
        context = ReportingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = ReportingSkillRegistry()
        skill = ReportingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
