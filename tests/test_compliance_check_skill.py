"""Tests for compliance_check skill."""

import pytest

from app.skills.compliance_check_skill import (
    ComplianceCheckSkill,
    ComplianceCheckSkillConfig,
    ComplianceCheckSkillContext,
)


class TestComplianceCheckSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ComplianceCheckSkill()
        context = ComplianceCheckSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = ComplianceCheckSkillConfig(name='test', description='desc')
        skill = ComplianceCheckSkill(config=config)
        assert skill.config.name == 'test'
