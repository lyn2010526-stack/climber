"""Tests for MemoryToolSet."""

from __future__ import annotations

import pytest

from app.tools.memory_toolset import MemoryToolSet


class FakeMemoryOrchestrator:
    """Fake orchestrator for testing."""

    def __init__(self, retrieval_result=None):
        self._retrieval_result = retrieval_result
        self.episodic_calls = []
        self.archival_calls = []
        self._persistent_memory_service = self
        self._vector_memory_service = None

    async def retrieve_for_query(self, user_id, agent_id, query, session_context=None):
        return self._retrieval_result

    async def create_episodic_memory(self, **kwargs):
        self.episodic_calls.append(kwargs)

    async def create_archival_passage(self, **kwargs):
        self.archival_calls.append(kwargs)


class FakeResult:
    """Fake MemoryRetrievalResult."""

    def __init__(self, core="", episodic="", archival="", reflection=""):
        self.core_memory = core
        self.episodic_context = episodic
        self.archival_context = archival
        self.reflection_context = reflection

    def format_for_prompt(self):
        parts = []
        if self.core_memory:
            parts.append(self.core_memory)
        if self.episodic_context:
            parts.append(f"[RELEVANT MEMORIES]\n{self.episodic_context}")
        if self.archival_context:
            parts.append(f"[ARCHIVAL KNOWLEDGE]\n{self.archival_context}")
        if self.reflection_context:
            parts.append(f"[PAST REFLECTIONS]\n{self.reflection_context}")
        return "\n\n".join(parts)


@pytest.mark.asyncio
async def test_get_tools_returns_three_tools():
    """Test that get_tools returns remember, recall, and forget."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)
    tools = toolset.get_tools()

    assert len(tools) == 3
    names = [t["function"]["name"] for t in tools]
    assert "remember" in names
    assert "recall" in names
    assert "forget" in names


@pytest.mark.asyncio
async def test_remember_creates_episodic_memory():
    """Test that remember tool creates an episodic memory."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="remember",
        arguments={"content": "User likes Python", "importance": 0.8, "memory_type": "episodic"},
        user_id="user1",
        agent_id="agent1",
    )

    assert "Remembered" in result
    assert len(orchestrator.episodic_calls) == 1
    assert orchestrator.episodic_calls[0]["content"] == "User likes Python"
    assert orchestrator.episodic_calls[0]["importance"] == 0.8


@pytest.mark.asyncio
async def test_remember_requires_content():
    """Test that remember tool requires content."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="remember",
        arguments={"importance": 0.8},
        user_id="user1",
        agent_id="agent1",
    )

    assert "Error" in result
    assert "content is required" in result


@pytest.mark.asyncio
async def test_recall_returns_memories():
    """Test that recall tool returns relevant memories."""
    fake_result = FakeResult(core="[CORE]\nI am helpful.", episodic="- User asked about Python")
    orchestrator = FakeMemoryOrchestrator(retrieval_result=fake_result)
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="recall",
        arguments={"query": "Python", "limit": 5},
        user_id="user1",
        agent_id="agent1",
    )

    assert "I am helpful" in result
    assert "User asked about Python" in result


@pytest.mark.asyncio
async def test_recall_requires_query():
    """Test that recall tool requires query."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="recall",
        arguments={"limit": 5},
        user_id="user1",
        agent_id="agent1",
    )

    assert "Error" in result
    assert "query is required" in result


@pytest.mark.asyncio
async def test_forget_returns_placeholder():
    """Test that forget tool returns placeholder (actual deletion not yet implemented)."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="forget",
        arguments={"memory_id": "mem_123", "reason": "outdated"},
        user_id="user1",
        agent_id="agent1",
    )

    # When memory doesn't exist, return "not found" message
    assert "mem_123" in result
    assert ("Forgot" in result) or ("not found" in result)


@pytest.mark.asyncio
async def test_forget_requires_memory_id():
    """Test that forget tool requires memory_id."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="forget",
        arguments={"reason": "outdated"},
        user_id="user1",
        agent_id="agent1",
    )

    assert "Error" in result
    assert "memory_id is required" in result


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    """Test that unknown tool returns error."""
    orchestrator = FakeMemoryOrchestrator()
    toolset = MemoryToolSet(orchestrator)

    result = await toolset.execute(
        tool_name="unknown_tool",
        arguments={},
        user_id="user1",
        agent_id="agent1",
    )

    assert "Unknown memory tool" in result
    assert "unknown_tool" in result
