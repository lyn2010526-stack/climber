"""Tests for code_review skill."""

import pytest

from app.skills.code_review_skill import (
    CodeReviewSkill,
    CodeReviewSkillConfig,
    CodeReviewSkillContext,
)


class TestCodeReviewSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = CodeReviewSkill()
        context = CodeReviewSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = CodeReviewSkillConfig(name='test', description='desc')
        skill = CodeReviewSkill(config=config)
        assert skill.config.name == 'test'
