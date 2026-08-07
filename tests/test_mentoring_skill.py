"""Tests for mentoring skill."""

import pytest

from app.skills.mentoring_skill import (
    MentoringSkill,
    MentoringSkillContext,
    MentoringSkillRegistry,
)


class TestMentoringSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = MentoringSkill()
        context = MentoringSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = MentoringSkillRegistry()
        skill = MentoringSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
