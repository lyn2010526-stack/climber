"""Tests for computer_vision skill."""

import pytest

from app.skills.computer_vision_skill import (
    ComputerVisionSkill,
    ComputerVisionSkillConfig,
    ComputerVisionSkillContext,
)


class TestComputerVisionSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = ComputerVisionSkill()
        context = ComputerVisionSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = ComputerVisionSkillConfig(name='test', description='desc')
        skill = ComputerVisionSkill(config=config)
        assert skill.config.name == 'test'
