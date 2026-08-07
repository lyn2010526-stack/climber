"""Tests for testing skill."""

import pytest

from app.skills.testing_skill import (
    TestingSkill,
    TestingSkillConfig,
    TestingSkillContext,
)


class TestTestingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = TestingSkill()
        context = TestingSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = TestingSkillConfig(name='test', description='desc')
        skill = TestingSkill(config=config)
        assert skill.config.name == 'test'
