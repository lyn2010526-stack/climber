"""Tests for code_generation skill."""

import pytest

from app.skills.code_generation_skill import (
    CodeGenerationSkill,
    CodeGenerationSkillConfig,
    CodeGenerationSkillContext,
)


class TestCodeGenerationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodeGenerationSkill()
        context = CodeGenerationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CodeGenerationSkillConfig(name='test', description='desc')
        skill = CodeGenerationSkill(config=config)
        assert skill.config.name == 'test'
