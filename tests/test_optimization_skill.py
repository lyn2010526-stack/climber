"""Tests for optimization skill."""

import pytest

from app.skills.optimization_skill import (
    OptimizationSkill,
    OptimizationSkillContext,
    OptimizationSkillRegistry,
)


class TestOptimizationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = OptimizationSkill()
        context = OptimizationSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = OptimizationSkillRegistry()
        skill = OptimizationSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
