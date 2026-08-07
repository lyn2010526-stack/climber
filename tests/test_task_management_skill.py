"""Tests for task_management skill."""

import pytest

from app.skills.task_management_skill import (
    TaskManagementSkill,
    TaskManagementSkillContext,
    TaskManagementSkillRegistry,
)


class TestTaskManagementSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = TaskManagementSkill()
        context = TaskManagementSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = TaskManagementSkillRegistry()
        skill = TaskManagementSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
