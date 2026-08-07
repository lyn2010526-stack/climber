"""Tests for analysis skill."""

import pytest

from app.skills.analysis_skill import (
    AnalysisSkill,
    AnalysisSkillContext,
    AnalysisSkillRegistry,
)


class TestAnalysisSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = AnalysisSkill()
        context = AnalysisSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = AnalysisSkillRegistry()
        skill = AnalysisSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
