"""AGI P2 Memory Layer tests.

Tests for agent persona system, memory lifecycle management,
cross-session personality inheritance, and persona-aware memory blocks.
"""

import os

os.environ["APP_TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_agi_p2_memory.db"

import pytest
import pytest_asyncio

from app.core.engine.memory_blocks import (
    BlockType,
    MemoryBlock,
    MemoryBlockStore,
    PersonaAwareBlockStore,
    create_persona_block,
)
from app.core.memory.lifecycle import MemoryLifecycleManager
from app.core.memory.persona import (
    AgentPersona,
    PersonaStore,
    create_session_persona,
    get_effective_persona,
    merge_session_persona,
)


@pytest_asyncio.fixture
async def persona_store():
    """Provide a clean persona store for each test."""
    store = PersonaStore()
    yield store


@pytest_asyncio.fixture
async def lifecycle_manager():
    """Provide a clean lifecycle manager for each test."""
    manager = MemoryLifecycleManager()
    yield manager


@pytest.fixture
def sample_persona():
    """Provide a sample persona for testing."""
    return AgentPersona(
        agent_id="agent-001",
        name="Climber",
        role="AI Coding Assistant",
        personality_traits=["analytical", "helpful", "precise"],
        expertise=["Python", "System Architecture", "Testing"],
        communication_style="Direct and concise",
        goals=["Help users build software", "Learn from interactions"],
    )


# ─── AgentPersona CRUD Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_persona_create_and_load(persona_store, sample_persona):
    """Test creating and loading a persona."""
    await persona_store.save(sample_persona)
    loaded = await persona_store.load("agent-001")

    assert loaded is not None
    assert loaded.agent_id == "agent-001"
    assert loaded.name == "Climber"
    assert loaded.role == "AI Coding Assistant"
    assert "analytical" in loaded.personality_traits
    assert "Python" in loaded.expertise
    assert loaded.communication_style == "Direct and concise"


@pytest.mark.asyncio
async def test_persona_update(persona_store, sample_persona):
    """Test updating persona fields."""
    await persona_store.save(sample_persona)
    updated = await persona_store.update(
        "agent-001",
        role="Senior AI Architect",
        communication_style="Detailed and thorough",
    )

    assert updated is not None
    assert updated.role == "Senior AI Architect"
    assert updated.communication_style == "Detailed and thorough"
    assert updated.name == "Climber"


@pytest.mark.asyncio
async def test_persona_delete(persona_store, sample_persona):
    """Test deleting a persona."""
    await persona_store.save(sample_persona)
    deleted = await persona_store.delete("agent-001")
    assert deleted is True

    loaded = await persona_store.load("agent-001")
    assert loaded is None


@pytest.mark.asyncio
async def test_persona_list_all(persona_store, sample_persona):
    """Test listing all personas."""
    await persona_store.save(sample_persona)
    persona2 = AgentPersona(
        agent_id="agent-002",
        name="Explorer",
        role="Research Assistant",
    )
    await persona_store.save(persona2)

    all_personas = await persona_store.list_all()
    assert len(all_personas) == 2
    ids = {p.agent_id for p in all_personas}
    assert "agent-001" in ids
    assert "agent-002" in ids


@pytest.mark.asyncio
async def test_persona_format_for_prompt(sample_persona):
    """Test persona formatting for system prompt."""
    prompt = sample_persona.format_for_prompt()
    assert "Climber" in prompt
    assert "AI Coding Assistant" in prompt
    assert "analytical" in prompt
    assert "Python" in prompt


@pytest.mark.asyncio
async def test_persona_load_nonexistent(persona_store):
    """Test loading a non-existent persona returns None."""
    loaded = await persona_store.load("nonexistent")
    assert loaded is None


# ─── MemoryLifecycleManager Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_write_memory(lifecycle_manager):
    """Test writing a new memory."""
    result = await lifecycle_manager.write_memory(
        content="User prefers functional programming style",
        user_id="user-001",
        agent_id="agent-001",
        memory_type="preference",
        importance=0.8,
    )

    assert result.memory_id is not None
    assert result.content == "User prefers functional programming style"
    assert result.user_id == "user-001"
    assert result.agent_id == "agent-001"
    assert result.memory_type == "preference"
    assert result.importance == 0.8


@pytest.mark.asyncio
async def test_index_memory(lifecycle_manager):
    """Test indexing a memory."""
    written = await lifecycle_manager.write_memory(
        content="Important project decision",
        user_id="user-001",
        importance=0.9,
    )
    indexed = await lifecycle_manager.index_memory(written.memory_id)
    assert indexed is True


@pytest.mark.asyncio
async def test_index_nonexistent_memory(lifecycle_manager):
    """Test indexing a non-existent memory returns False."""
    indexed = await lifecycle_manager.index_memory("nonexistent-id")
    assert indexed is False


@pytest.mark.asyncio
async def test_retrieve_memories(lifecycle_manager):
    """Test retrieving memories with query."""
    await lifecycle_manager.write_memory(
        content="User likes Python for backend development",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.8,
    )
    await lifecycle_manager.write_memory(
        content="User prefers TypeScript for frontend",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.7,
    )
    await lifecycle_manager.write_memory(
        content="Unrelated topic about cooking",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.5,
    )

    results = await lifecycle_manager.retrieve_memories(
        query="Python backend",
        user_id="user-001",
        limit=5,
    )

    assert len(results) > 0
    assert any("Python" in r.content for r in results)


@pytest.mark.asyncio
async def test_retrieve_memories_with_agent_filter(lifecycle_manager):
    """Test retrieving memories filtered by agent."""
    await lifecycle_manager.write_memory(
        content="Agent 1 memory about Python",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.8,
    )
    await lifecycle_manager.write_memory(
        content="Agent 2 memory about Python",
        user_id="user-001",
        agent_id="agent-002",
        importance=0.7,
    )

    results = await lifecycle_manager.retrieve_memories(
        query="Python",
        user_id="user-001",
        agent_id="agent-001",
        limit=10,
    )

    assert all(r.agent_id == "agent-001" or r.agent_id == "" for r in results)


@pytest.mark.asyncio
async def test_forget_memory(lifecycle_manager):
    """Test soft-deleting a memory."""
    written = await lifecycle_manager.write_memory(
        content="Temporary note to forget",
        user_id="user-001",
        importance=0.3,
    )
    forgotten = await lifecycle_manager.forget_memory(written.memory_id)
    assert forgotten is True

    results = await lifecycle_manager.retrieve_memories(
        query="Temporary",
        user_id="user-001",
        limit=10,
    )
    assert all(r.memory_id != written.memory_id for r in results)


@pytest.mark.asyncio
async def test_forget_nonexistent_memory(lifecycle_manager):
    """Test forgetting a non-existent memory returns False."""
    result = await lifecycle_manager.forget_memory("nonexistent-id")
    assert result is False


@pytest.mark.asyncio
async def test_decay_memories(lifecycle_manager):
    """Test memory importance decay."""
    await lifecycle_manager.write_memory(
        content="Old memory that should decay",
        user_id="user-001",
        agent_id="agent-001",
        importance=1.0,
    )

    report = await lifecycle_manager.decay_memories(
        user_id="user-001",
        agent_id="agent-001",
    )

    assert report.total_memories >= 1
    assert report.avg_importance_before >= report.avg_importance_after


@pytest.mark.asyncio
async def test_archive_old_memories(lifecycle_manager):
    """Test archiving old, low-importance memories."""
    await lifecycle_manager.write_memory(
        content="Low importance old memory",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.1,
    )

    report = await lifecycle_manager.archive_old_memories(
        user_id="user-001",
        agent_id="agent-001",
        threshold_days=0,
    )

    assert report.archived_count >= 1


@pytest.mark.asyncio
async def test_archive_preserves_high_importance(lifecycle_manager):
    """Test that high-importance memories are not archived."""
    await lifecycle_manager.write_memory(
        content="High importance memory",
        user_id="user-001",
        agent_id="agent-001",
        importance=0.9,
    )

    report = await lifecycle_manager.archive_old_memories(
        user_id="user-001",
        agent_id="agent-001",
        threshold_days=0,
    )

    assert report.archived_count == 0
    assert report.remaining_count >= 1


# ─── Cross-Session Personality Inheritance Tests ───────────────────────────


@pytest.mark.asyncio
async def test_create_session_persona():
    """Test creating a session-specific persona."""
    session_persona = create_session_persona(
        session_id="session-001",
        base_persona_id="agent-001",
        overrides={"communication_style": "More casual"},
    )

    assert session_persona["session_id"] == "session-001"
    assert session_persona["base_persona_id"] == "agent-001"
    assert session_persona["overrides"]["communication_style"] == "More casual"


@pytest.mark.asyncio
async def test_get_effective_persona_with_overrides(persona_store, sample_persona):
    """Test getting effective persona with session overrides applied."""
    await persona_store.save(sample_persona)

    effective = await get_effective_persona(
        session_id=None,
        agent_id="agent-001",
    )

    assert effective is not None
    assert effective.name == "Climber"
    assert effective.role == "AI Coding Assistant"


@pytest.mark.asyncio
async def test_get_effective_persona_nonexistent():
    """Test getting effective persona for non-existent agent returns None."""
    effective = await get_effective_persona(
        session_id=None,
        agent_id="nonexistent",
    )
    assert effective is None


@pytest.mark.asyncio
async def test_merge_session_persona_nonexistent():
    """Test merging a non-existent session persona returns None."""
    report = await merge_session_persona("nonexistent-session")
    assert report is None


# ─── Memory Block Operations with Persona Tests ─────────────────────────────


def test_create_persona_block():
    """Test creating a persona memory block."""
    persona_data = {
        "name": "Climber",
        "role": "AI Assistant",
        "personality_traits": ["analytical", "helpful"],
        "expertise": ["Python", "Testing"],
        "communication_style": "Direct",
        "goals": ["Help users"],
    }

    block = create_persona_block("agent-001", persona_data)

    assert block.block_type == BlockType.PERSONA
    assert block.label == "persona_agent-001"
    assert "Climber" in block.value
    assert "analytical" in block.value
    assert "Python" in block.value


def test_persona_aware_block_store():
    """Test persona-aware block store operations."""
    store = PersonaAwareBlockStore()

    block1 = MemoryBlock(
        label="persona_agent1",
        value="Agent 1 persona",
        block_type=BlockType.PERSONA,
    )
    block2 = MemoryBlock(
        label="context_session1",
        value="Session context",
        block_type=BlockType.CONTEXT,
    )

    store.add_block(block1, agent_id="agent-001")
    store.add_block(block2, agent_id="agent-001")

    agent_blocks = store.list_blocks(agent_id="agent-001")
    assert len(agent_blocks) == 2

    all_blocks = store.list_blocks()
    assert len(all_blocks) == 2


def test_persona_aware_block_store_update():
    """Test updating blocks in persona-aware store."""
    store = PersonaAwareBlockStore()

    block = MemoryBlock(
        label="persona_test",
        value="Original value",
        block_type=BlockType.PERSONA,
    )
    store.add_block(block, agent_id="agent-001")

    updated = store.update_block("persona_test", "Updated value")
    assert updated is True

    retrieved = store.get_block("persona_test")
    assert retrieved is not None
    assert retrieved.value == "Updated value"


def test_persona_aware_block_store_compile_prompt():
    """Test compiling persona-aware blocks into prompt."""
    store = PersonaAwareBlockStore()

    block = create_persona_block("agent-001", {
        "name": "TestAgent",
        "role": "Tester",
        "personality_traits": ["thorough"],
        "expertise": ["QA"],
        "communication_style": "Detailed",
        "goals": ["Find bugs"],
    })
    store.add_block(block, agent_id="agent-001")

    prompt = store.compile_prompt(agent_id="agent-001")
    assert "TestAgent" in prompt
    assert "Tester" in prompt


def test_block_type_persona_exists():
    """Test that PERSONA block type is defined."""
    assert hasattr(BlockType, "PERSONA")
    assert BlockType.PERSONA.value == "persona"


def test_memory_block_store_get_block():
    """Test MemoryBlockStore get_block method."""
    store = MemoryBlockStore()
    block = MemoryBlock(label="test_block", value="test value")
    store.add_block(block)

    retrieved = store.get_block("test_block")
    assert retrieved is not None
    assert retrieved.value == "test value"


def test_memory_block_store_update_block():
    """Test MemoryBlockStore update_block method."""
    store = MemoryBlockStore()
    block = MemoryBlock(label="updatable", value="original")
    store.add_block(block)

    updated = store.update_block("updatable", "updated value")
    assert updated is True

    retrieved = store.get_block("updatable")
    assert retrieved is not None
    assert retrieved.value == "updated value"


def test_memory_block_store_list_blocks():
    """Test MemoryBlockStore list_blocks method."""
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="block1", value="value1"))
    store.add_block(MemoryBlock(label="block2", value="value2", block_type=BlockType.PERSONA))

    all_blocks = store.list_blocks()
    assert len(all_blocks) == 2

    persona_blocks = store.list_blocks(block_type=BlockType.PERSONA)
    assert len(persona_blocks) == 1
    assert persona_blocks[0].label == "block2"
