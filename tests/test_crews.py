"""Tests for multi-agent collaboration system."""

from __future__ import annotations

from app.multi_agent import AgentRole, AgentTask, TaskStatus
from app.multi_agent.crew import Crew


class TestAgentRole:
    def test_create_agent_role(self):
        agent = AgentRole(
            name="researcher",
            role="Senior Research Analyst",
            goal="Find accurate information on any topic",
            backstory="You are an experienced researcher with attention to detail.",
            tools=["web_search", "fetch_url"],
        )
        assert agent.name == "researcher"
        assert agent.can_delegate is True
        assert "web_search" in agent.tools

    def test_minimal_agent_role(self):
        agent = AgentRole(
            name="writer",
            role="Content Writer",
            goal="Write clear content",
            backstory="You are a skilled writer.",
        )
        assert agent.tools == []
        assert agent.can_delegate is True


class TestAgentTask:
    def test_create_task(self):
        task = AgentTask(
            description="Research Python async patterns",
            expected_output="A summary of key patterns",
            agent_name="researcher",
        )
        assert task.status == TaskStatus.PENDING
        assert task.result == ""
        assert task.id is not None

    def test_task_with_context(self):
        task = AgentTask(
            description="Write an article",
            expected_output="A 500-word article",
            agent_name="writer",
            context="Target audience: developers",
        )
        assert task.context == "Target audience: developers"


class TestCrew:
    def test_crew_initialization(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        agents = [
            AgentRole(name="a1", role="Role1", goal="Goal1", backstory="Story1"),
            AgentRole(name="a2", role="Role2", goal="Goal2", backstory="Story2"),
        ]
        tasks = [
            AgentTask(description="Task1", expected_output="Out1", agent_name="a1"),
            AgentTask(description="Task2", expected_output="Out2", agent_name="a2"),
        ]
        crew = Crew(agents=agents, tasks=tasks, engine=engine)
        assert len(crew.agents) == 2
        assert len(crew.tasks) == 2
        assert crew.crew_id is not None

    def test_crew_missing_agent(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        agents = [AgentRole(name="a1", role="R", goal="G", backstory="B")]
        tasks = [
            AgentTask(description="T", expected_output="O", agent_name="nonexistent"),
        ]
        crew = Crew(agents=agents, tasks=tasks, engine=engine)
        assert "nonexistent" not in crew.agents

    def test_build_initial_context(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        agents = [
            AgentRole(name="researcher", role="Analyst", goal="Find info", backstory="Exp"),
            AgentRole(name="writer", role="Writer", goal="Write content", backstory="Skill"),
        ]
        tasks = [
            AgentTask(description="Research topic", expected_output="Summary", agent_name="researcher"),
            AgentTask(description="Write article", expected_output="Article", agent_name="writer"),
        ]
        crew = Crew(agents=agents, tasks=tasks, engine=engine)
        context = crew._build_initial_context()
        assert "researcher" in context
        assert "writer" in context
        assert "Research topic" in context
        assert "Write article" in context

    def test_build_agent_system_prompt(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        agent = AgentRole(
            name="researcher",
            role="Senior Analyst",
            goal="Find accurate info",
            backstory="10 years experience",
        )
        crew = Crew(agents=[agent], tasks=[], engine=engine)
        prompt = crew._build_agent_system_prompt(agent, "Some context")
        assert "researcher" in prompt
        assert "Senior Analyst" in prompt
        assert "Find accurate info" in prompt
        assert "Some context" in prompt

    def test_build_task_message(self):
        from unittest.mock import MagicMock

        engine = MagicMock(spec=AgentEngine)
        crew = Crew(agents=[], tasks=[], engine=engine)
        task = AgentTask(
            description="Analyze data",
            expected_output="Report",
            agent_name="analyst",
            context="Use Python",
        )
        msg = crew._build_task_message(task, "ctx")
        assert "Analyze data" in msg
        assert "Report" in msg
        assert "Use Python" in msg


# Need to import AgentEngine for spec
from app.core.agent_engine import AgentEngine
