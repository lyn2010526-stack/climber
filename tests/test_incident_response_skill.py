"""Tests for incident_response skill."""

import pytest

from app.skills.incident_response_skill import (
    IncidentResponseSkill,
    IncidentResponseSkillConfig,
    IncidentResponseSkillContext,
)


class TestIncidentResponseSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = IncidentResponseSkill()
        context = IncidentResponseSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = IncidentResponseSkillConfig(name='test', description='desc')
        skill = IncidentResponseSkill(config=config)
        assert skill.config.name == 'test'
