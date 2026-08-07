"""Tests for question_answering skill."""

import pytest

from app.skills.question_answering_skill import (
    QuestionAnsweringSkill,
    QuestionAnsweringSkillConfig,
    QuestionAnsweringSkillContext,
)


class TestQuestionAnsweringSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = QuestionAnsweringSkill()
        context = QuestionAnsweringSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = QuestionAnsweringSkillConfig(name='test', description='desc')
        skill = QuestionAnsweringSkill(config=config)
        assert skill.config.name == 'test'
