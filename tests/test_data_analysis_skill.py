"""Tests for data_analysis skill."""

import pytest

from app.skills.data_analysis_skill import (
    DataAnalysisSkill,
    DataAnalysisSkillConfig,
    DataAnalysisSkillContext,
)


class TestDataAnalysisSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DataAnalysisSkill()
        context = DataAnalysisSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DataAnalysisSkillConfig(name='test', description='desc')
        skill = DataAnalysisSkill(config=config)
        assert skill.config.name == 'test'
