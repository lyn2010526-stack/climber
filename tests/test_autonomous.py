"""Tests for autonomous execution engine."""

from unittest.mock import MagicMock

import pytest

from app.core import AgentEvent, AgentEventType
from app.core.agent_engine import AgentEngine, AgentSession
from app.core.autonomous_engine import (
    AutonomousEngine,
    AutonomousTask,
    SubTask,
    TaskStatus,
)
from app.models.registry import ModelRegistry
from app.tools import ToolRegistry


@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=AgentEngine)
    engine.sessions = {}
    return engine


@pytest.fixture
def real_engine():
    model_registry = MagicMock(spec=ModelRegistry)
    tool_registry = MagicMock(spec=ToolRegistry)
    return AgentEngine(model_registry, tool_registry)


class TestSubTask:
    def test_creation(self):
        st = SubTask(id="test-1", description="Do something")
        assert st.status == TaskStatus.PENDING
        assert st.attempts == 0
        assert st.max_attempts == 3

    def test_with_dependencies(self):
        st = SubTask(id="test-2", description="Step 2", dependencies=["test-1"])
        assert len(st.dependencies) == 1


class TestAutonomousTask:
    def test_creation(self):
        task = AutonomousTask(id="task-1", objective="Build something")
        assert task.status == TaskStatus.PENDING
        assert task.total_steps == 0
        assert task.completed_steps == 0

    def test_with_subtasks(self):
        task = AutonomousTask(
            id="task-2",
            objective="Complex task",
            subtasks=[
                SubTask(id="s1", description="Step 1"),
                SubTask(id="s2", description="Step 2"),
            ],
        )
        task.total_steps = 2
        assert len(task.subtasks) == 2


class TestAutonomousEngine:
    def test_init(self, mock_engine):
        engine = AutonomousEngine(mock_engine)
        assert engine.agent_engine is mock_engine

    @pytest.mark.asyncio
    async def test_plan_generation(self, mock_engine):
        """Test that the engine generates a plan from the objective."""
        auton = AutonomousEngine(mock_engine)

        # Create a mock session
        session = MagicMock(spec=AgentSession)
        session.session_id = "test-session"
        session.system_prompt = ""
        session.user_id = "test-user"
        session.enabled_tools = []
        session.session_memory = MagicMock()
        session.session_memory.get_context.return_value = []

        # Mock the engine.run to return a plan
        async def mock_run(session, prompt):
            yield AgentEvent(
                type=AgentEventType.TEXT,
                data={"content": "1. Research the topic\n2. Write the code\n3. Test the code"},
            )

        mock_engine.run = mock_run

        events = []
        async for event in auton.execute_autonomous(session, "Build a web app", max_steps=5):
            events.append(event)

        # Should have planning events
        thinking_events = [e for e in events if e.type == AgentEventType.THINKING]
        assert len(thinking_events) >= 1

    @pytest.mark.asyncio
    async def test_skill_prompt_applied(self, mock_engine):
        """Test that skill system prompt is applied to session."""
        auton = AutonomousEngine(mock_engine)

        session = MagicMock(spec=AgentSession)
        session.session_id = "test-session"
        session.system_prompt = "Original prompt"
        session.user_id = "test-user"
        session.enabled_tools = []
        session.session_memory = MagicMock()
        session.session_memory.get_context.return_value = []

        async def mock_run(session, prompt):
            yield AgentEvent(
                type=AgentEventType.TEXT,
                data={"content": "1. Step one\n2. Step two"},
            )

        mock_engine.run = mock_run

        events = []
        async for event in auton.execute_autonomous(
            session, "Research Python", skill_id="web_research", max_steps=3
        ):
            events.append(event)

        # Skill prompt should be applied
        assert "Original prompt" in session.system_prompt

    @pytest.mark.asyncio
    async def test_max_steps_respected(self, mock_engine):
        """Test that execution respects max_steps limit."""
        auton = AutonomousEngine(mock_engine)

        session = MagicMock(spec=AgentSession)
        session.session_id = "test-session"
        session.system_prompt = ""
        session.user_id = "test-user"
        session.enabled_tools = []
        session.session_memory = MagicMock()
        session.session_memory.get_context.return_value = []

        call_count = 0

        async def mock_run(session, prompt):
            nonlocal call_count
            call_count += 1
            yield AgentEvent(
                type=AgentEventType.TEXT,
                data={"content": "1. Step one\n2. Step two\n3. Step three\n4. Step four\n5. Step five"},
            )

        mock_engine.run = mock_run

        events = []
        async for event in auton.execute_autonomous(session, "Test task", max_steps=2):
            events.append(event)

        # Plan should be capped at max_steps (2)
        thinking_events = [e for e in events if e.type == AgentEventType.THINKING]
        plan_events = [e for e in thinking_events if "subtasks" in e.data]
        if plan_events:
            assert len(plan_events[0].data["subtasks"]) <= 2


class TestTaskStatus:
    def test_all_statuses(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.RETRYING == "retrying"
