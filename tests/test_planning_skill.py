"""Tests for planning skill."""

import pytest

from app.skills.planning_skill import (
    PlanningSkill,
    PlanningSkillContext,
    PlanningSkillRegistry,
)


class TestPlanningSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = PlanningSkill()
        context = PlanningSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = PlanningSkillRegistry()
        skill = PlanningSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
