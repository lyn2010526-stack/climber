"""Tests for project_management skill."""

import pytest

from app.skills.project_management_skill import (
    ProjectManagementSkill,
    ProjectManagementSkillContext,
    ProjectManagementSkillRegistry,
)


class TestProjectManagementSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ProjectManagementSkill()
        context = ProjectManagementSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = ProjectManagementSkillRegistry()
        skill = ProjectManagementSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
