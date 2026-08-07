"""Tests for summarization skill."""

import pytest

from app.skills.summarization_skill import (
    SummarizationSkill,
    SummarizationSkillConfig,
    SummarizationSkillContext,
)


class TestSummarizationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = SummarizationSkill()
        context = SummarizationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = SummarizationSkillConfig(name='test', description='desc')
        skill = SummarizationSkill(config=config)
        assert skill.config.name == 'test'
