"""Tests for review skill."""

import pytest

from app.skills.review_skill import (
    ReviewSkill,
    ReviewSkillContext,
    ReviewSkillRegistry,
)


class TestReviewSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ReviewSkill()
        context = ReviewSkillContext(agent_id='test')
        result = await skill.execute(context)
        assert result['success']

    def test_registry(self):
        registry = ReviewSkillRegistry()
        skill = ReviewSkill()
        registry.register(skill)
        assert registry.get(skill.name) is not None
