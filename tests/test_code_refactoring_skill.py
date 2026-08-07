"""Tests for code_refactoring skill."""

import pytest

from app.skills.code_refactoring_skill import (
    CodeRefactoringSkill,
    CodeRefactoringSkillConfig,
    CodeRefactoringSkillContext,
)


class TestCodeRefactoringSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodeRefactoringSkill()
        context = CodeRefactoringSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CodeRefactoringSkillConfig(name='test', description='desc')
        skill = CodeRefactoringSkill(config=config)
        assert skill.config.name == 'test'
