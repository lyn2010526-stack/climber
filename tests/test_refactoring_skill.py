"""Tests for refactoring skill."""

import pytest

from app.skills.refactoring_skill import (
    RefactoringSkill,
    RefactoringSkillContext,
    RefactoringSkillRegistry,
)


class TestRefactoringSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = RefactoringSkill()
        context = RefactoringSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = RefactoringSkillRegistry()
        skill = RefactoringSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
