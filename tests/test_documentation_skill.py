"""Tests for documentation skill."""

import pytest

from app.skills.documentation_skill import (
    DocumentationSkill,
    DocumentationSkillConfig,
    DocumentationSkillContext,
)


class TestDocumentationSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DocumentationSkill()
        context = DocumentationSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DocumentationSkillConfig(name='test', description='desc')
        skill = DocumentationSkill(config=config)
        assert skill.config.name == 'test'
