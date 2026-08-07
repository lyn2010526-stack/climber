"""Tests for dependency_check skill."""

import pytest

from app.skills.dependency_check_skill import (
    DependencyCheckSkill,
    DependencyCheckSkillConfig,
    DependencyCheckSkillContext,
)


class TestDependencyCheckSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DependencyCheckSkill()
        context = DependencyCheckSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DependencyCheckSkillConfig(name='test', description='desc')
        skill = DependencyCheckSkill(config=config)
        assert skill.config.name == 'test'
