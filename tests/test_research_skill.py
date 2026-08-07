"""Tests for research skill."""

import pytest

from app.skills.research_skill import (
    ResearchSkill,
    ResearchSkillContext,
    ResearchSkillRegistry,
)


class TestResearchSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ResearchSkill()
        context = ResearchSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = ResearchSkillRegistry()
        skill = ResearchSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
