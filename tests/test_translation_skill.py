"""Tests for translation skill."""

import pytest

from app.skills.translation_skill import (
    TranslationSkill,
    TranslationSkillConfig,
    TranslationSkillContext,
)


class TestTranslationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = TranslationSkill()
        context = TranslationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = TranslationSkillConfig(name='test', description='desc')
        skill = TranslationSkill(config=config)
        assert skill.config.name == 'test'
