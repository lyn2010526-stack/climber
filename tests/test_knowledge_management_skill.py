"""Tests for knowledge_management skill."""

import pytest

from app.skills.knowledge_management_skill import (
    KnowledgeManagementSkill,
    KnowledgeManagementSkillContext,
    KnowledgeManagementSkillRegistry,
)


class TestKnowledgeManagementSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = KnowledgeManagementSkill()
        context = KnowledgeManagementSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = KnowledgeManagementSkillRegistry()
        skill = KnowledgeManagementSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
