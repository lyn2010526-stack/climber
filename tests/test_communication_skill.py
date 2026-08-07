"""Tests for communication skill."""

import pytest

from app.skills.communication_skill import (
    CommunicationSkill,
    CommunicationSkillContext,
    CommunicationSkillRegistry,
)


class TestCommunicationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CommunicationSkill()
        context = CommunicationSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = CommunicationSkillRegistry()
        skill = CommunicationSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
