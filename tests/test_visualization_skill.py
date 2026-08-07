"""Tests for visualization skill."""

import pytest

from app.skills.visualization_skill import (
    VisualizationSkill,
    VisualizationSkillContext,
    VisualizationSkillRegistry,
)


class TestVisualizationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = VisualizationSkill()
        context = VisualizationSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = VisualizationSkillRegistry()
        skill = VisualizationSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
