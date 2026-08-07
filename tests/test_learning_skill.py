"""Tests for learning skill."""

import pytest

from app.skills.learning_skill import (
    LearningSkill,
    LearningSkillContext,
    LearningSkillRegistry,
)


class TestLearningSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = LearningSkill()
        context = LearningSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = LearningSkillRegistry()
        skill = LearningSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
