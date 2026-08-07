"""Tests for coding skill."""

import pytest

from app.skills.coding_skill import (
    CodingSkill,
    CodingSkillContext,
    CodingSkillRegistry,
)


class TestCodingSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodingSkill()
        context = CodingSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = CodingSkillRegistry()
        skill = CodingSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
