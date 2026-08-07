"""Tests for security_audit skill."""

import pytest

from app.skills.security_audit_skill import (
    SecurityAuditSkill,
    SecurityAuditSkillConfig,
    SecurityAuditSkillContext,
)


class TestSecurityAuditSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = SecurityAuditSkill()
        context = SecurityAuditSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = SecurityAuditSkillConfig(name='test', description='desc')
        skill = SecurityAuditSkill(config=config)
        assert skill.config.name == 'test'
