"""Tests for ContextPreparer."""

from __future__ import annotations

import pytest

from app.core.context_preparer import ContextPreparer
from app.core import MessageRole


class FakeMemoryOrchestrator:
    """Fake orchestrator for testing."""

    def __init__(self, result=None):
        self._result = result
        self.calls = []

    async def retrieve_for_query(self, user_id, agent_id, query, session_context=None):
        self.calls.append({
            "user_id": user_id,
            "agent_id": agent_id,
            "query": query,
            "session_context": session_context,
        })
        return self._result


class FakeCoreMemoryService:
    """Fake core memory service for testing."""

    def __init__(self, blocks=None):
        self._blocks = blocks or []
        self.calls = []

    async def get_blocks(self, user_id, agent_id=None):
        self.calls.append({"user_id": user_id, "agent_id": agent_id})
        return self._blocks

    def format_for_prompt(self, blocks):
        return "<core_memory>test</core_memory>"


class FakeMemoryResult:
    """Fake MemoryRetrievalResult."""

    def __init__(self, core_memory="", episodic="", archival="", reflection="", profile=""):
        self.core_memory = core_memory
        self.episodic_context = episodic
        self.archival_context = archival
        self.reflection_context = reflection
        self.user_profile = profile

    def format_for_prompt(self):
        parts = []
        if self.core_memory:
            parts.append(self.core_memory)
        if self.user_profile:
            parts.append(f"[USER PROFILE]\n{self.user_profile}")
        if self.episodic_context:
            parts.append(f"[RELEVANT MEMORIES]\n{self.episodic_context}")
        if self.archival_context:
            parts.append(f"[ARCHIVAL KNOWLEDGE]\n{self.archival_context}")
        if self.reflection_context:
            parts.append(f"[PAST REFLECTIONS]\n{self.reflection_context}")
        return "\n\n".join(parts)


class FakeSession:
    """Fake session for testing."""

    def __init__(self, user_id="user1", agent_id="agent1"):
        self.user_id = user_id
        self.agent_id = agent_id
        self.messages = []


@pytest.mark.asyncio
async def test_prepare_injects_memories_into_session():
    """Test that prepare injects retrieved memories into session.messages."""
    result = FakeMemoryResult(
        core_memory="[CORE]\nI am a helpful assistant.",
        episodic="- User asked about Python\n- User asked about async",
    )
    orchestrator = FakeMemoryOrchestrator(result=result)
    core_memory = FakeCoreMemoryService(blocks=[])
    
    preparer = ContextPreparer(
        memory_orchestrator=orchestrator,
        core_memory_service=core_memory,
    )
    
    session = FakeSession(user_id="user1", agent_id="agent1")
    session.messages.append({"role": MessageRole.SYSTEM, "content": "You are helpful."})
    session.messages.append({"role": MessageRole.USER, "content": "Hello"})
    
    await preparer.prepare(session, "Hello")
    
    # Should have injected memory before the last message (insert(-1))
    assert len(session.messages) == 3
    injected = session.messages[1]  # inserted before last message
    assert injected["role"] == MessageRole.SYSTEM
    assert "I am a helpful assistant" in injected["content"]
    assert "User asked about Python" in injected["content"]
    
    # Verify orchestrator was called
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]["user_id"] == "user1"
    assert orchestrator.calls[0]["agent_id"] == "agent1"
    assert orchestrator.calls[0]["query"] == "Hello"


@pytest.mark.asyncio
async def test_prepare_injects_core_memory_blocks():
    """Test that prepare injects core memory blocks."""
    result = FakeMemoryResult(core_memory="")
    orchestrator = FakeMemoryOrchestrator(result=result)
    
    blocks = [type('Block', (), {'label': 'persona', 'value': 'I am helpful.', 'description': '', 'read_only': False})]
    core_memory = FakeCoreMemoryService(blocks=blocks)
    
    preparer = ContextPreparer(
        memory_orchestrator=orchestrator,
        core_memory_service=core_memory,
    )
    
    session = FakeSession(user_id="user1", agent_id="agent1")
    session.messages.append({"role": MessageRole.SYSTEM, "content": "You are helpful."})
    session.messages.append({"role": MessageRole.USER, "content": "Hello"})
    
    await preparer.prepare(session, "Hello")
    
    # Should have injected core memory before last message
    assert len(session.messages) == 3
    injected = session.messages[1]  # inserted before last message
    assert injected["role"] == MessageRole.SYSTEM
    assert injected["content"] == "<core_memory>test</core_memory>"
    
    # Verify core memory service was called
    assert len(core_memory.calls) == 1
    assert core_memory.calls[0]["user_id"] == "user1"


@pytest.mark.asyncio
async def test_prepare_handles_orchestrator_failure_gracefully():
    """Test that prepare continues even if orchestrator fails."""
    class FailingOrchestrator:
        async def retrieve_for_query(self, *args, **kwargs):
            raise RuntimeError("DB connection failed")
    
    core_memory = FakeCoreMemoryService(blocks=[])
    preparer = ContextPreparer(
        memory_orchestrator=FailingOrchestrator(),
        core_memory_service=core_memory,
    )
    
    session = FakeSession(user_id="user1", agent_id="agent1")
    session.messages.append({"role": MessageRole.SYSTEM, "content": "You are helpful."})
    session.messages.append({"role": MessageRole.USER, "content": "Hello"})
    
    # Should not raise
    await preparer.prepare(session, "Hello")
    
    # Messages should be unchanged (no injection from orchestrator)
    assert len(session.messages) == 2


@pytest.mark.asyncio
async def test_prepare_handles_core_memory_failure_gracefully():
    """Test that prepare continues even if core memory fails."""
    result = FakeMemoryResult(core_memory="[CORE]\nTest")
    orchestrator = FakeMemoryOrchestrator(result=result)
    
    class FailingCoreMemory:
        async def get_blocks(self, *args, **kwargs):
            raise RuntimeError("DB connection failed")
    
    preparer = ContextPreparer(
        memory_orchestrator=orchestrator,
        core_memory_service=FailingCoreMemory(),
    )
    
    session = FakeSession(user_id="user1", agent_id="agent1")
    session.messages.append({"role": MessageRole.SYSTEM, "content": "You are helpful."})
    session.messages.append({"role": MessageRole.USER, "content": "Hello"})
    
    # Should not raise
    await preparer.prepare(session, "Hello")
    
    # Should have injected from orchestrator but not core memory
    assert len(session.messages) == 3
    injected = session.messages[1]  # inserted before last message
    assert injected["role"] == MessageRole.SYSTEM
    assert "[CORE]" in injected["content"]
