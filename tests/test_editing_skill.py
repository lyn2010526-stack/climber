"""Tests for editing skill."""

import pytest

from app.skills.editing_skill import (
    EditingSkill,
    EditingSkillContext,
    EditingSkillRegistry,
)


class TestEditingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = EditingSkill()
        context = EditingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = EditingSkillRegistry()
        skill = EditingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
