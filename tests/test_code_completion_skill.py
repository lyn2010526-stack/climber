"""Tests for code_completion skill."""

import pytest

from app.skills.code_completion_skill import (
    CodeCompletionSkill,
    CodeCompletionSkillConfig,
    CodeCompletionSkillContext,
)


class TestCodeCompletionSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodeCompletionSkill()
        context = CodeCompletionSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CodeCompletionSkillConfig(name='test', description='desc')
        skill = CodeCompletionSkill(config=config)
        assert skill.config.name == 'test'
