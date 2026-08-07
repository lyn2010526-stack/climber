"""Tests for writing skill."""

import pytest

from app.skills.writing_skill import (
    WritingSkill,
    WritingSkillContext,
    WritingSkillRegistry,
)


class TestWritingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = WritingSkill()
        context = WritingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = WritingSkillRegistry()
        skill = WritingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
