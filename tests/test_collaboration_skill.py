"""Tests for collaboration skill."""

import pytest

from app.skills.collaboration_skill import (
    CollaborationSkill,
    CollaborationSkillContext,
    CollaborationSkillRegistry,
)


class TestCollaborationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CollaborationSkill()
        context = CollaborationSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = CollaborationSkillRegistry()
        skill = CollaborationSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
