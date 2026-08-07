"""Tests for capacity_planning skill."""

import pytest

from app.skills.capacity_planning_skill import (
    CapacityPlanningSkill,
    CapacityPlanningSkillConfig,
    CapacityPlanningSkillContext,
)


class TestCapacityPlanningSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CapacityPlanningSkill()
        context = CapacityPlanningSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CapacityPlanningSkillConfig(name='test', description='desc')
        skill = CapacityPlanningSkill(config=config)
        assert skill.config.name == 'test'
