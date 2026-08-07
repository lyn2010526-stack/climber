"""Tests for backup_management skill."""

import pytest

from app.skills.backup_management_skill import (
    BackupManagementSkill,
    BackupManagementSkillConfig,
    BackupManagementSkillContext,
)


class TestBackupManagementSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = BackupManagementSkill()
        context = BackupManagementSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = BackupManagementSkillConfig(name='test', description='desc')
        skill = BackupManagementSkill(config=config)
        assert skill.config.name == 'test'
