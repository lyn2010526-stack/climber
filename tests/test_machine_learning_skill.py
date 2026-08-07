"""Tests for machine_learning skill."""

import pytest

from app.skills.machine_learning_skill import (
    MachineLearningSkill,
    MachineLearningSkillConfig,
    MachineLearningSkillContext,
)


class TestMachineLearningSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = MachineLearningSkill()
        context = MachineLearningSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = MachineLearningSkillConfig(name='test', description='desc')
        skill = MachineLearningSkill(config=config)
        assert skill.config.name == 'test'
