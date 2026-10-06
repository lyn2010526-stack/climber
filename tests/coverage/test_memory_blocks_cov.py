"""Coverage tests for app.core.engine.memory_blocks.

Self-contained, deterministic, no network / external services.
"""

from __future__ import annotations

import time

from app.core.engine.memory_blocks import (
    BlockType,
    EntityExtractor,
    MemoryBlock,
    MemoryBlockStore,
    MemoryConsolidator,
    PassageRecord,
    PersonaAwareBlockStore,
    create_persona_block,
)


# --------------------------------------------------------------------------- #
# BlockType / MemoryBlock / PassageRecord
# --------------------------------------------------------------------------- #
def test_block_type_values():
    assert BlockType.CORE == "core"
    assert {b.value for b in BlockType} == {
        "core",
        "user",
        "archive",
        "entity",
        "context",
        "persona",
    }


def test_memory_block_update_normal():
    block = MemoryBlock(label="a", value="old", limit=100)
    before = block.updated_at
    time.sleep(0)  # yield only
    assert block.update("new") is True
    assert block.value == "new"
    assert block.updated_at >= before


def test_memory_block_update_readonly_returns_false():
    block = MemoryBlock(label="a", value="old", read_only=True)
    assert block.update("new") is False
    assert block.value == "old"


def test_memory_block_update_truncates_over_limit():
    block = MemoryBlock(label="a", value="", limit=5)
    assert block.update("abcdefghij") is True
    assert block.value == "abcde"


def test_memory_block_to_dict():
    block = MemoryBlock(label="a", value="v", block_type=BlockType.USER, limit=10)
    d = block.to_dict()
    assert d["block_id"] == block.block_id
    assert d["label"] == "a"
    assert d["value"] == "v"
    assert d["block_type"] == "user"
    assert d["read_only"] is False
    assert d["limit"] == 10
    assert d["description"] == ""
    assert d["updated_at"] == block.updated_at


def test_passage_record_defaults():
    p = PassageRecord(content="hello")
    assert p.content == "hello"
    assert p.source == ""
    assert isinstance(p.passage_id, str)
    assert p.metadata == {}
    assert isinstance(p.timestamp, float)


# --------------------------------------------------------------------------- #
# MemoryBlockStore
# --------------------------------------------------------------------------- #
def test_store_add_get_update_remove():
    store = MemoryBlockStore()
    block = MemoryBlock(label="core", value="v")
    bid = store.add_block(block)
    assert bid == block.block_id
    assert store.get_block("core") is block
    assert store.get_block("missing") is None

    assert store.update_block("core", "v2") is True
    assert store.get_block("core").value == "v2"
    assert store.update_block("missing", "x") is False

    assert store.remove_block("core") is True
    assert store.get_block("core") is None
    assert store.remove_block("core") is False


def test_store_remove_readonly_returns_false():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="ro", value="v", read_only=True))
    assert store.remove_block("ro") is False
    assert store.get_block("ro") is not None


def test_store_list_blocks_and_filter():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="a", value="1", block_type=BlockType.CORE))
    store.add_block(MemoryBlock(label="b", value="2", block_type=BlockType.USER))

    assert len(store.list_blocks()) == 2
    users = store.list_blocks(BlockType.USER)
    assert [b.label for b in users] == ["b"]
    assert store.list_blocks(BlockType.ARCHIVE) == []


def test_store_compile_prompt_variants():
    store = MemoryBlockStore()
    assert store.compile_prompt() == ""

    store.add_block(MemoryBlock(label="a", value="1", block_type=BlockType.CORE))
    store.add_block(MemoryBlock(label="b", value="2", block_type=BlockType.USER))

    full = store.compile_prompt()
    assert "### a\n1" in full
    assert "### b\n2" in full

    only_user = store.compile_prompt(include_types=[BlockType.USER])
    assert only_user == "### b\n2"

    assert store.compile_prompt(include_types=[BlockType.ARCHIVE]) == ""


def test_store_archive_add_and_cap():
    store = MemoryBlockStore()
    store._max_archive_size = 2  # keep the test cheap
    for i in range(3):
        pid = store.add_passage(f"p{i}")
        assert isinstance(pid, str)
    # On overflow the list is trimmed to [-max//2:] == last 1 entry.
    assert store.get_stats()["archive_size"] == 1


def test_store_add_passage_with_source_and_metadata():
    store = MemoryBlockStore()
    store.add_passage("content", source="src", metadata={"k": "v"})
    assert store._archive[0].source == "src"
    assert store._archive[0].metadata == {"k": "v"}


def test_store_search_archive_ranking_and_limit():
    store = MemoryBlockStore()
    store.add_passage("alpha beta gamma")
    store.add_passage("alpha only")
    store.add_passage("")  # no content words -> skipped
    store.add_passage("unrelated words here")

    results = store.search_archive("alpha beta")
    assert [p.content for p in results][:2] == [
        "alpha beta gamma",
        "alpha only",
    ]

    limited = store.search_archive("alpha", max_results=1)
    assert len(limited) == 1


def test_store_search_archive_no_match():
    store = MemoryBlockStore()
    store.add_passage("hello world")
    assert store.search_archive("xyz") == []
    assert store.search_archive("") == []


def test_store_get_stats():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="a", value="1234", block_type=BlockType.CORE))
    store.add_block(MemoryBlock(label="b", value="56", block_type=BlockType.USER))
    store.add_block(MemoryBlock(label="c", value="7", block_type=BlockType.USER))
    store.add_passage("x")

    stats = store.get_stats()
    assert stats["total_blocks"] == 3
    assert stats["type_distribution"] == {"core": 1, "user": 2}
    assert stats["archive_size"] == 1
    assert stats["total_chars"] == 7


# --------------------------------------------------------------------------- #
# EntityExtractor
# --------------------------------------------------------------------------- #
def test_entity_extractor_extract_all_types():
    text = (
        "John Smith emailed jane.doe@example.com about https://example.com/page "
        "on 2024-01-02, inspect a/b/.py"
    )
    entities = EntityExtractor.extract(text)
    assert "person" in entities
    assert "email" in entities
    assert entities["email"] == ["jane.doe@example.com"]
    assert "url" in entities
    assert "date" in entities
    assert entities["date"] == ["2024-01-02"]
    assert "file_path" in entities
    # NOTE: the file_path pattern only matches a path segment that is
    # immediately followed by the dotted extension (see bug report).
    assert entities["file_path"] == ["a/b/.py"]


def test_entity_extractor_file_path_pattern_misses_normal_paths():
    # Documented real bug: the file_path regex fails to match ordinary paths
    # such as ``src/main.py``.
    assert "file_path" not in EntityExtractor.extract("see src/main.py")


def test_entity_extractor_extract_empty():
    assert EntityExtractor.extract("nothing to see here") == {}


def test_entity_extractor_dedupes():
    entities = EntityExtractor.extract("John Smith and John Smith again")
    assert entities["person"] == ["John Smith"]


def test_entity_extractor_to_block_with_entities():
    block = EntityExtractor.extract_to_block("Contact jane@example.com today", label="ents")
    assert block.label == "ents"
    assert block.block_type == BlockType.ENTITY
    assert block.read_only is False
    assert "email: jane@example.com" in block.value


def test_entity_extractor_to_block_without_entities():
    block = EntityExtractor.extract_to_block("plain words only")
    assert block.value == "No entities detected."


# --------------------------------------------------------------------------- #
# MemoryConsolidator
# --------------------------------------------------------------------------- #
def test_consolidate_prunes_empty_editable_blocks():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="empty", value="   "))
    store.add_block(MemoryBlock(label="keep", value="content"))
    store.add_block(MemoryBlock(label="ro_empty", value="", read_only=True))

    report = MemoryConsolidator(store).consolidate()
    assert report["blocks_pruned"] == 1
    assert store.get_block("empty") is None
    assert store.get_block("keep") is not None
    assert store.get_block("ro_empty") is not None


def test_consolidate_indexes_archive_into_entity_block():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="entities", value="old", block_type=BlockType.ENTITY))
    store.add_passage("reach jane@example.com please")
    store.add_passage("no entities in this passage at all")

    report = MemoryConsolidator(store).consolidate()
    assert report["archive_indexed"] == 2
    assert "jane@example.com" in store.get_block("entities").value


def test_consolidate_without_entity_block():
    store = MemoryBlockStore()
    store.add_passage("reach jane@example.com please")
    report = MemoryConsolidator(store).consolidate()
    assert report["archive_indexed"] == 0


def test_consolidate_skips_readonly_entity_block():
    store = MemoryBlockStore()
    store.add_block(
        MemoryBlock(label="entities", value="old", block_type=BlockType.ENTITY, read_only=True)
    )
    store.add_passage("reach jane@example.com please")
    report = MemoryConsolidator(store).consolidate()
    assert report["archive_indexed"] == 0
    assert store.get_block("entities").value == "old"


def test_consolidate_no_passages_and_no_entities():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="entities", value="old", block_type=BlockType.ENTITY))
    report = MemoryConsolidator(store).consolidate()
    assert report["archive_indexed"] == 0

    store.add_passage("plain text with no entity patterns")
    report2 = MemoryConsolidator(store).consolidate()
    assert report2["archive_indexed"] == 0


def test_detect_stale_blocks():
    store = MemoryBlockStore()
    store.add_block(MemoryBlock(label="fresh", value="v"))
    store.add_block(MemoryBlock(label="ro", value="v", read_only=True))
    stale = MemoryConsolidator(store).detect_stale_blocks(max_age_seconds=-1)
    assert stale == ["fresh"]

    fresh_only = MemoryConsolidator(store).detect_stale_blocks(max_age_seconds=86400 * 30)
    assert fresh_only == []


# --------------------------------------------------------------------------- #
# create_persona_block
# --------------------------------------------------------------------------- #
def test_create_persona_block_full():
    block = create_persona_block(
        "agent1",
        {
            "name": "Ada",
            "role": "engineer",
            "personality_traits": ["curious", "precise"],
            "expertise": ["python", "testing"],
            "communication_style": "concise",
            "goals": ["ship", "learn"],
        },
    )
    assert block.label == "persona_agent1"
    assert block.block_type == BlockType.PERSONA
    assert "Agent: Ada" in block.value
    assert "Role: engineer" in block.value
    assert "Traits: curious, precise" in block.value
    assert "Expertise: python, testing" in block.value
    assert "Style: concise" in block.value
    assert "Goals:" in block.value
    assert "  - ship" in block.value
    assert block.metadata == {"agent_id": "agent1", "source": "persona_system"}


def test_create_persona_block_minimal():
    block = create_persona_block("agent2", {})
    assert block.value == "Agent: Unknown"
    assert block.description == "Persona for agent agent2"


# --------------------------------------------------------------------------- #
# PersonaAwareBlockStore
# --------------------------------------------------------------------------- #
def test_persona_store_add_with_and_without_agent():
    store = PersonaAwareBlockStore()
    b1 = MemoryBlock(label="p1", value="v1")
    b2 = MemoryBlock(label="p2", value="v2")
    store.add_block(b1, agent_id="a1")
    store.add_block(b2)
    store.add_block(MemoryBlock(label="p3", value="v3"), agent_id="a1")

    assert store.get_block("p1") is b1
    assert store.get_block("missing") is None
    assert {b.label for b in store.list_blocks()} == {"p1", "p2", "p3"}
    assert {b.label for b in store.list_blocks(agent_id="a1")} == {"p1", "p3"}
    # Unknown agent falls back to all blocks.
    assert {b.label for b in store.list_blocks(agent_id="unknown")} == {"p1", "p2", "p3"}


def test_persona_store_update_remove_compile():
    store = PersonaAwareBlockStore()
    store.add_block(MemoryBlock(label="p1", value="v1"), agent_id="a1")

    assert store.update_block("p1", "v2") is True
    assert store.get_block("p1").value == "v2"
    assert store.update_block("missing", "x") is False

    assert store.compile_prompt(agent_id="a1") == "### p1\nv2"
    assert store.compile_prompt(agent_id="no-agent") == "### p1\nv2"
    assert store.remove_block("p1") is True
    assert store.compile_prompt(agent_id="a1") == ""
