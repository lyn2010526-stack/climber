"""Tests for teaching skill."""

import pytest

from app.skills.teaching_skill import (
    TeachingSkill,
    TeachingSkillContext,
    TeachingSkillRegistry,
)


class TestTeachingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = TeachingSkill()
        context = TeachingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = TeachingSkillRegistry()
        skill = TeachingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
