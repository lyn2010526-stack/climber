"""Tests for cost_optimization skill."""

import pytest

from app.skills.cost_optimization_skill import (
    CostOptimizationSkill,
    CostOptimizationSkillConfig,
    CostOptimizationSkillContext,
)


class TestCostOptimizationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CostOptimizationSkill()
        context = CostOptimizationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CostOptimizationSkillConfig(name='test', description='desc')
        skill = CostOptimizationSkill(config=config)
        assert skill.config.name == 'test'
