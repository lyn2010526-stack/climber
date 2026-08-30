"""Tests for delegation tools in hierarchical crews."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.engine.hierarchical import AgentSpec, HierarchicalCrew, TaskAssignment
from app.tools import ToolRegistry


class FakeEngine:
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        answer: str = "The dependency is ready.",
    ) -> None:
        self.tool_registry = tool_registry or ToolRegistry()
        self.answer = answer
        self.sessions: list[Any] = []
        self.delegation_results: list[str] = []

    def create_session(self, **kwargs: Any) -> Any:
        session = SimpleNamespace(**kwargs)
        self.sessions.append(session)
        return session

    async def run(self, session: Any, message: str):
        session.last_message = message
        await asyncio.sleep(0)
        if session.agent_id.startswith("hierarchical-lead-") and "ask_question" in session.tools:
            if "Ask a focused question" in message:
                result = await self.tool_registry.execute(
                    "ask_question",
                    {"agent_name": "researcher", "question": "What did you find?"},
                )
            else:
                result = await self.tool_registry.execute(
                    "delegate_work",
                    {
                        "agent_name": "researcher",
                        "description": "Research the dependency",
                        "expected_output": "A concise finding",
                    },
                )
            self.delegation_results.append(result)
            yield SimpleNamespace(type=SimpleNamespace(value="text"), data={"content": result})
            return

        yield SimpleNamespace(
            type=SimpleNamespace(value="text"),
            data={"content": self.answer},
        )


def _crew(engine: FakeEngine, *, can_delegate: bool = True) -> HierarchicalCrew:
    return HierarchicalCrew(
        agents=[
            AgentSpec(
                name="lead",
                role="Lead",
                goal="Coordinate delivery",
                backstory="Experienced lead",
                tools=["read_file"],
                can_delegate=can_delegate,
            ),
            AgentSpec(
                name="researcher",
                role="Researcher",
                goal="Find facts",
                backstory="Careful researcher",
                can_delegate=False,
            ),
        ],
        engine=engine,
        verbose=False,
    )


@pytest.mark.asyncio
async def test_delegating_agent_receives_collaboration_tools() -> None:
    engine = FakeEngine()
    crew = _crew(engine)

    await crew._execute_with_verification(
        TaskAssignment(
            agent_name="lead",
            description="Complete the implementation",
            expected_output="Working result",
        ),
        "Shared context",
    )

    assert engine.sessions[0].tools == ["read_file", "delegate_work", "ask_question"]
    assert engine.delegation_results == ["The dependency is ready."]
    assert engine.sessions[1].tools == []


@pytest.mark.asyncio
async def test_non_delegating_agent_does_not_receive_collaboration_tools() -> None:
    engine = FakeEngine()
    crew = _crew(engine, can_delegate=False)

    await crew._execute_with_verification(
        TaskAssignment(
            agent_name="lead",
            description="Complete the implementation",
            expected_output="Working result",
        ),
        "Shared context",
    )

    assert engine.sessions[0].tools == ["read_file"]


@pytest.mark.asyncio
async def test_ask_question_routes_to_named_coworker() -> None:
    engine = FakeEngine()
    crew = _crew(engine)

    result = await crew._execute_with_verification(
        TaskAssignment(
            agent_name="lead",
            description="Ask a focused question",
            expected_output="The answer",
        ),
        "Shared context",
    )

    assert result == "The dependency is ready."
    assert "What did you find?" in engine.sessions[1].last_message


@pytest.mark.asyncio
async def test_concurrent_crews_isolate_delegation_context() -> None:
    registry = ToolRegistry()
    first_engine = FakeEngine(registry, answer="First crew result")
    second_engine = FakeEngine(registry, answer="Second crew result")
    first_crew = _crew(first_engine)
    second_crew = _crew(second_engine)
    assignment = TaskAssignment(
        agent_name="lead",
        description="Complete the implementation",
        expected_output="Working result",
    )

    first_result, second_result = await asyncio.gather(
        first_crew._execute_with_verification(assignment, "First context"),
        second_crew._execute_with_verification(assignment, "Second context"),
    )

    assert first_result == "First crew result"
    assert second_result == "Second crew result"
