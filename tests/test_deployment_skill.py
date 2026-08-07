"""Tests for deployment skill."""

import pytest

from app.skills.deployment_skill import (
    DeploymentSkill,
    DeploymentSkillConfig,
    DeploymentSkillContext,
)


class TestDeploymentSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = DeploymentSkill()
        context = DeploymentSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = DeploymentSkillConfig(name='test', description='desc')
        skill = DeploymentSkill(config=config)
        assert skill.config.name == 'test'
