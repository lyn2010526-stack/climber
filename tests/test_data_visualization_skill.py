"""Tests for data_visualization skill."""

import pytest

from app.skills.data_visualization_skill import (
    DataVisualizationSkill,
    DataVisualizationSkillConfig,
    DataVisualizationSkillContext,
)


class TestDataVisualizationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DataVisualizationSkill()
        context = DataVisualizationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DataVisualizationSkillConfig(name='test', description='desc')
        skill = DataVisualizationSkill(config=config)
        assert skill.config.name == 'test'
