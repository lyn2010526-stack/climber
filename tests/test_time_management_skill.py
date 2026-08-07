"""Tests for time_management skill."""

import pytest

from app.skills.time_management_skill import (
    TimeManagementSkill,
    TimeManagementSkillContext,
    TimeManagementSkillRegistry,
)


class TestTimeManagementSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = TimeManagementSkill()
        context = TimeManagementSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = TimeManagementSkillRegistry()
        skill = TimeManagementSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
