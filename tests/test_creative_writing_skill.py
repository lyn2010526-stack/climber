"""Tests for creative_writing skill."""

import pytest

from app.skills.creative_writing_skill import (
    CreativeWritingSkill,
    CreativeWritingSkillContext,
    CreativeWritingSkillRegistry,
)


class TestCreativeWritingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CreativeWritingSkill()
        context = CreativeWritingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = CreativeWritingSkillRegistry()
        skill = CreativeWritingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
