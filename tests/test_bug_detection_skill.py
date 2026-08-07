"""Tests for bug_detection skill."""

import pytest

from app.skills.bug_detection_skill import (
    BugDetectionSkill,
    BugDetectionSkillConfig,
    BugDetectionSkillContext,
)


class TestBugDetectionSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = BugDetectionSkill()
        context = BugDetectionSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = BugDetectionSkillConfig(name='test', description='desc')
        skill = BugDetectionSkill(config=config)
        assert skill.config.name == 'test'
