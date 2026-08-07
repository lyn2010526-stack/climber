"""Tests for log_analysis skill."""

import pytest

from app.skills.log_analysis_skill import (
    LogAnalysisSkill,
    LogAnalysisSkillConfig,
    LogAnalysisSkillContext,
)


class TestLogAnalysisSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = LogAnalysisSkill()
        context = LogAnalysisSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = LogAnalysisSkillConfig(name='test', description='desc')
        skill = LogAnalysisSkill(config=config)
        assert skill.config.name == 'test'
