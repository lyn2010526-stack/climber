"""Tests for performance_tuning skill."""

import pytest

from app.skills.performance_tuning_skill import (
    PerformanceTuningSkill,
    PerformanceTuningSkillConfig,
    PerformanceTuningSkillContext,
)


class TestPerformanceTuningSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = PerformanceTuningSkill()
        context = PerformanceTuningSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = PerformanceTuningSkillConfig(name='test', description='desc')
        skill = PerformanceTuningSkill(config=config)
        assert skill.config.name == 'test'
