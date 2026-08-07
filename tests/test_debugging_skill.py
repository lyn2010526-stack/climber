"""Tests for debugging skill."""

import pytest

from app.skills.debugging_skill import (
    DebuggingSkill,
    DebuggingSkillConfig,
    DebuggingSkillContext,
)


class TestDebuggingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DebuggingSkill()
        context = DebuggingSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DebuggingSkillConfig(name='test', description='desc')
        skill = DebuggingSkill(config=config)
        assert skill.config.name == 'test'
