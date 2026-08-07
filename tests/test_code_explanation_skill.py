"""Tests for code_explanation skill."""

import pytest

from app.skills.code_explanation_skill import (
    CodeExplanationSkill,
    CodeExplanationSkillConfig,
    CodeExplanationSkillContext,
)


class TestCodeExplanationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodeExplanationSkill()
        context = CodeExplanationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CodeExplanationSkillConfig(name='test', description='desc')
        skill = CodeExplanationSkill(config=config)
        assert skill.config.name == 'test'
