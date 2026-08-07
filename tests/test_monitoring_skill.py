"""Tests for monitoring skill."""

import pytest

from app.skills.monitoring_skill import (
    MonitoringSkill,
    MonitoringSkillConfig,
    MonitoringSkillContext,
)


class TestMonitoringSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = MonitoringSkill()
        context = MonitoringSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = MonitoringSkillConfig(name='test', description='desc')
        skill = MonitoringSkill(config=config)
        assert skill.config.name == 'test'
