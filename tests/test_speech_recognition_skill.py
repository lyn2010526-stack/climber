"""Tests for speech_recognition skill."""

import pytest

from app.skills.speech_recognition_skill import (
    SpeechRecognitionSkill,
    SpeechRecognitionSkillConfig,
    SpeechRecognitionSkillContext,
)


class TestSpeechRecognitionSkill:
    """Tests for skill."""

    @pytest.mark.asyncio
    async def test_execute(self):
        skill = SpeechRecognitionSkill()
        context = SpeechRecognitionSkillContext(session_id='test')
        result = await skill.execute(context, action='test')
        assert result.success is True
        assert result.output is not None

    def test_config(self):
        config = SpeechRecognitionSkillConfig(name='test', description='desc')
        skill = SpeechRecognitionSkill(config=config)
        assert skill.config.name == 'test'
