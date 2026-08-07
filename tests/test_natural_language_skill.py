"""Tests for natural_language skill."""

import pytest

from app.skills.natural_language_skill import (
    NaturalLanguageSkill,
    NaturalLanguageSkillConfig,
    NaturalLanguageSkillContext,
)


class TestNaturalLanguageSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = NaturalLanguageSkill()
        context = NaturalLanguageSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = NaturalLanguageSkillConfig(name='test', description='desc')
        skill = NaturalLanguageSkill(config=config)
        assert skill.config.name == 'test'
